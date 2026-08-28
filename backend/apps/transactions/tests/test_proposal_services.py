import pytest
from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.services.pricing.totals_compute import _d
from apps.orgs.models import OrgBase


class ProposalTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Proposal."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.proposal = Proposal.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_d_helper_function(self):
        """Test the _d helper function for decimal conversion."""
        # Test valid decimal conversion
        self.assertEqual(_d(10.5), Decimal('10.50'))
        self.assertEqual(_d("15.75"), Decimal('15.75'))
        self.assertEqual(_d(20), Decimal('20.00'))

        # Test invalid input (should return 0)
        self.assertEqual(_d("invalid"), Decimal('0.00'))
        self.assertEqual(_d(None), Decimal('0.00'))
        self.assertEqual(_d(""), Decimal('0.00'))

        # Test rounding
        self.assertEqual(_d(10.123, places=2), Decimal('10.12'))
        self.assertEqual(_d(10.123, places=3), Decimal('10.123'))

    def test_totals_empty_proposal(self):
        """Test totals computation for proposal with no lines."""
        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertEqual(totals['subtotal'], 0.0)
        self.assertEqual(totals['total'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['margin'], 0.0)

    def test_totals_single_line(self):
        """Test totals computation for proposal with single line item."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Test Item'},
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertIn('margin', totals)
        # Totals should be non-zero since we have a line
        self.assertGreater(totals['total'], 0)

    def test_totals_multiple_lines(self):
        """Test totals computation for proposal with multiple line items."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 1'},
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 2'},
            quantity={'staged': 3, 'remaining': 3},
            price={'unit': 5.00, 'extended': 15.00},
            cost={'unit': 4.00, 'extended': 12.00}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertGreater(totals['total'], 0)

    def test_totals_zero_sell_price(self):
        """Test totals computation when sell price is zero (division by zero protection)."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Free Item'},
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 0.00, 'extended': 0.00},
            cost={'unit': 5.00, 'extended': 5.00}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertEqual(totals['total'], 0.00)
        # margin_pc should be 0 or None when subtotal is 0
        self.assertIn(totals['margin_pc'], (None, 0.0))

    def test_totals_missing_price_data(self):
        """Test totals computation with missing or incomplete price data."""
        # Create line with missing price data
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Incomplete Item'},
            quantity={'staged': 1, 'remaining': 1},
            price={},  # Empty price dict
            cost={}    # Empty cost dict
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        # Should handle missing data gracefully (return zeros)
        self.assertEqual(totals['subtotal'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['total'], 0.0)

    def test_totals_all_cost_components(self):
        """Test totals computation with all cost components present."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Complete Item'},
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={
                'unit': 80.00,
                'extended': 80.00,
                'shipping': 5.00,
                'handling': 2.00,
            }
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertGreater(totals['total'], 0)
