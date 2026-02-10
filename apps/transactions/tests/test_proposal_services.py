import pytest
from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.services.proposal_totals import compute_proposal_sell_cost_totals, _d
from apps.core.models import Contact


class ProposalTotalsServiceTest(TestCase):
    """Test cases for proposal_totals service functions."""

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

    def test_compute_proposal_sell_cost_totals_empty_proposal(self):
        """Test totals computation for proposal with no lines."""
        result = compute_proposal_sell_cost_totals(self.proposal)

        # Should return default structure with zeros
        self.assertIn('sell', result)
        self.assertIn('cost', result)
        self.assertIn('totals', result)

        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['sell']['discount'], 0.0)
        self.assertEqual(result['sell']['total'], 0.0)

        self.assertEqual(result['cost']['line_sum_goods'], 0.0)
        self.assertEqual(result['cost']['total'], 0.0)

        self.assertEqual(result['totals']['total'], 0.0)
        self.assertEqual(result['totals']['cost'], 0.0)
        self.assertEqual(result['totals']['margin'], 0.0)
        self.assertIsNone(result['totals']['margin_pc'])

    def test_compute_proposal_sell_cost_totals_single_line(self):
        """Test totals computation for proposal with single line item."""
        # Create a line item
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Test Item'},
            quantity={'placed': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00, 'discount_amount': 1.00},
            cost={'extended': 16.00, 'tax': 1.60, 'shipping': 0.50}
        )

        result = compute_proposal_sell_cost_totals(self.proposal)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 20.00)  # 2 * 10.00
        self.assertEqual(result['sell']['discount'], 1.00)
        self.assertEqual(result['sell']['total'], 20.00)  # No tax/shipping in sell total

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 16.00)
        self.assertEqual(result['cost']['line_sum_tax'], 1.60)
        self.assertEqual(result['cost']['line_sum_shipping'], 0.50)
        self.assertEqual(result['cost']['total'], 18.10)  # 16 + 1.60 + 0.50 + 0 + 0

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 20.00)
        self.assertEqual(result['totals']['cost'], 18.10)
        self.assertEqual(result['totals']['margin'], 1.90)  # 20.00 - 18.10
        self.assertAlmostEqual(result['totals']['margin_pc'], 9.50, places=2)  # (1.90/20.00)*100

    def test_compute_proposal_sell_cost_totals_multiple_lines(self):
        """Test totals computation for proposal with multiple line items."""
        # Create multiple line items
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 1'},
            quantity={'placed': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'extended': 16.00}
        )
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Item 2'},
            quantity={'placed': 3, 'remaining': 3},
            price={'unit': 5.00, 'extended': 15.00, 'discount_amount': 2.00},
            cost={'extended': 12.00, 'tax': 0.60}
        )

        result = compute_proposal_sell_cost_totals(self.proposal)

        # Check sell totals (sum of all lines)
        self.assertEqual(result['sell']['line_sum_goods'], 35.00)  # 20.00 + 15.00
        self.assertEqual(result['sell']['discount'], 2.00)
        self.assertEqual(result['sell']['total'], 35.00)

        # Check cost totals (sum of all lines)
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)  # 16.00 + 12.00
        self.assertEqual(result['cost']['line_sum_tax'], 0.60)
        self.assertEqual(result['cost']['total'], 28.60)  # 28.00 + 0.60

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 35.00)
        self.assertEqual(result['totals']['cost'], 28.60)
        self.assertEqual(result['totals']['margin'], 6.40)  # 35.00 - 28.60
        self.assertAlmostEqual(result['totals']['margin_pc'], 18.29, places=2)  # (6.40/35.00)*100

    def test_compute_proposal_sell_cost_totals_zero_sell_price(self):
        """Test totals computation when sell price is zero (division by zero protection)."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Free Item'},
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 0.00, 'extended': 0.00},
            cost={'extended': 5.00}
        )

        result = compute_proposal_sell_cost_totals(self.proposal)

        self.assertEqual(result['totals']['total'], 0.00)
        self.assertEqual(result['totals']['cost'], 5.00)
        self.assertEqual(result['totals']['margin'], -5.00)
        self.assertIsNone(result['totals']['margin_pc'])  # Should be None due to division by zero

    def test_compute_proposal_sell_cost_totals_missing_price_data(self):
        """Test totals computation with missing or incomplete price data."""
        # Create line with missing price data
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Incomplete Item'},
            quantity={'placed': 1, 'remaining': 1},
            price={},  # Empty price dict
            cost={}    # Empty cost dict
        )

        result = compute_proposal_sell_cost_totals(self.proposal)

        # Should handle missing data gracefully (return zeros)
        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['cost']['line_sum_goods'], 0.0)
        self.assertEqual(result['totals']['total'], 0.0)
        self.assertEqual(result['totals']['cost'], 0.0)

    def test_compute_proposal_sell_cost_totals_all_cost_components(self):
        """Test totals computation with all cost components present."""
        ProposalLine.objects.create(
            proposal=self.proposal,
            item={'description': 'Complete Item'},
            quantity={'placed': 1, 'remaining': 1},
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

        result = compute_proposal_sell_cost_totals(self.proposal)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 100.00)
        self.assertEqual(result['sell']['total'], 100.00)

        # Check cost totals (all components included)
        self.assertEqual(result['cost']['line_sum_goods'], 80.00)
        self.assertEqual(result['cost']['line_sum_tax'], 8.00)
        self.assertEqual(result['cost']['line_sum_shipping'], 5.00)
        self.assertEqual(result['cost']['handling'], 3.00)
        self.assertEqual(result['cost']['freight'], 3.00)
        self.assertEqual(result['cost']['commissions'], 4.00)
        self.assertEqual(result['cost']['total'], 103.00)  # 80 + 8 + 5 + 2 + 3 + 4

        # Check margin
        self.assertEqual(result['totals']['total'], 100.00)
        self.assertEqual(result['totals']['cost'], 103.00)
        self.assertEqual(result['totals']['margin'], -3.00)  # 100 - 103
        self.assertAlmostEqual(result['totals']['margin_pc'], -3.00, places=2)