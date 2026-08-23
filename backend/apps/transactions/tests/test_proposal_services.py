import pytest
from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.services.totals import _d
from apps.core.models import Contact


class ProposalTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Proposal."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
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
        self.assertEqual(totals['discount'], 0.0)
        self.assertEqual(totals['total'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['margin'], 0.0)
        self.assertIsNone(totals['margin_pc'])

    def test_totals_single_line(self):
        """Test totals computation for proposal with single line item."""
        # Create a line item
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Test Item'},
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00, 'discount_amount': 1.00},
            cost={'extended': 16.00, 'tax': 1.60, 'shipping': 0.50}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        # Check sell totals
        self.assertEqual(totals['subtotal'], 20.00)  # 2 * 10.00
        self.assertEqual(totals['discount'], 1.00)
        self.assertEqual(totals['total'], 20.00)

        # Check cost total
        self.assertEqual(totals['cost'], 18.10)  # 16 + 1.60 + 0.50

        # Check margin calculations
        self.assertEqual(totals['margin'], 1.90)  # 20.00 - 18.10
        self.assertAlmostEqual(totals['margin_pc'], 9.50, places=2)  # (1.90/20.00)*100

    def test_totals_multiple_lines(self):
        """Test totals computation for proposal with multiple line items."""
        # Create multiple line items
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 1'},
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'extended': 16.00}
        )
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 2'},
            quantity={'staged': 3, 'remaining': 3},
            price={'unit': 5.00, 'extended': 15.00, 'discount_amount': 2.00},
            cost={'extended': 12.00, 'tax': 0.60}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        # Check totals (sum of all lines)
        self.assertEqual(totals['subtotal'], 35.00)  # 20.00 + 15.00
        self.assertEqual(totals['discount'], 2.00)
        self.assertEqual(totals['total'], 35.00)
        self.assertEqual(totals['cost'], 28.60)  # 28.00 + 0.60
        self.assertEqual(totals['margin'], 6.40)  # 35.00 - 28.60
        self.assertAlmostEqual(totals['margin_pc'], 18.29, places=2)  # (6.40/35.00)*100

    def test_totals_zero_sell_price(self):
        """Test totals computation when sell price is zero (division by zero protection)."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Free Item'},
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 0.00, 'extended': 0.00},
            cost={'extended': 5.00}
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        self.assertEqual(totals['total'], 0.00)
        self.assertEqual(totals['cost'], 5.00)
        self.assertEqual(totals['margin'], -5.00)
        self.assertIsNone(totals['margin_pc'])  # Should be None due to division by zero

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
                'extended': 80.00,
                'tax': 8.00,
                'shipping': 5.00,
                'handling': 2.00,
                'freight': 3.00,
                'commissions': 4.00
            }
        )

        self.proposal.update_sell_cost_totals(persist=True)
        self.proposal.refresh_from_db()

        totals = self.proposal.totals
        # Check totals
        self.assertEqual(totals['subtotal'], 100.00)
        self.assertEqual(totals['total'], 100.00)
        self.assertEqual(totals['cost'], 102.00)  # 80 + 8 + 5 + 2 + 3 + 4
        self.assertEqual(totals['margin'], -2.00)  # 100 - 102
        self.assertAlmostEqual(totals['margin_pc'], -2.00, places=2)
