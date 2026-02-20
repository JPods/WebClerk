from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Order, OrderLine
from apps.transactions.services.order_totals import compute_order_sell_cost_totals
from apps.core.models import Contact


class OrderTotalsServiceTest(TestCase):
    """Test cases for order totals service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_compute_totals_empty_order(self):
        """Test computing totals for an empty order."""
        result = compute_order_sell_cost_totals(self.order)

        expected = {
            'sell': {
                'line_sum_goods': 0.0,
                'discount': 0.0,
                'tax': 0.0,
                'shipping': 0.0,
                'handling': 0.0,
                'other': 0.0,
                'total': 0.0,
            },
            'cost': {
                'line_sum_goods': 0.0,
                'line_sum_tax': 0.0,
                'line_sum_shipping': 0.0,
                'line_sum_handling': 0.0,
                'freight': 0.0,
                'commissions': 0.0,
                'tax_rate': None,
                'tax': 0.0,
                'total': 0.0,
            },
            'totals': {
                'total': 0.0,
                'cost': 0.0,
                'margin': 0.0,
                'margin_pc': None,
                'received': None,
                'balance': None,
            }
        }
        self.assertEqual(result, expected)

    def test_compute_totals_with_lines(self):
        """Test computing totals with line items."""
        # Create line items
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'placed': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 2'},
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        result = compute_order_sell_cost_totals(self.order)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 35.00)
        self.assertEqual(result['sell']['total'], 35.00)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)
        self.assertEqual(result['cost']['total'], 28.00)

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 35.00)
        self.assertEqual(result['totals']['cost'], 28.00)
        self.assertEqual(result['totals']['margin'], 7.00)
        self.assertAlmostEqual(result['totals']['margin_pc'], 20.00, places=2)

    def test_compute_totals_with_discounts(self):
        """Test computing totals with discounts."""
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 100.00, 'discount_amount': 10.00, 'extended': 90.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        result = compute_order_sell_cost_totals(self.order)

        # Check sell totals include discount
        self.assertEqual(result['sell']['line_sum_goods'], 90.00)
        self.assertEqual(result['sell']['discount'], 10.00)
        self.assertEqual(result['sell']['total'], 90.00)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 80.00)
        self.assertEqual(result['cost']['total'], 80.00)

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 90.00)
        self.assertEqual(result['totals']['cost'], 80.00)
        self.assertEqual(result['totals']['margin'], 10.00)
        self.assertAlmostEqual(result['totals']['margin_pc'], 11.11, places=2)

    def test_compute_totals_with_additional_costs(self):
        """Test computing totals with additional cost components."""
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={
                'unit': 80.00,
                'extended': 80.00,
                'shipping': 5.00,
                'handling': 2.00,
                'freight': 3.00,
                'commissions': 4.00,
                'tax': 6.00
            }
        )

        result = compute_order_sell_cost_totals(self.order)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 100.00)
        self.assertEqual(result['sell']['total'], 100.00)

        # Check cost totals include all components
        self.assertEqual(result['cost']['line_sum_goods'], 80.00)
        self.assertEqual(result['cost']['line_sum_shipping'], 5.00)
        self.assertEqual(result['cost']['line_sum_handling'], 2.00)
        self.assertEqual(result['cost']['freight'], 3.00)
        self.assertEqual(result['cost']['commissions'], 4.00)
        self.assertEqual(result['cost']['tax'], 6.00)
        self.assertEqual(result['cost']['total'], 100.00)  # 80 + 5 + 2 + 3 + 4 + 6

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 100.00)
        self.assertEqual(result['totals']['cost'], 100.00)
        self.assertEqual(result['totals']['margin'], 0.00)
        self.assertAlmostEqual(result['totals']['margin_pc'], 0.00, places=2)
