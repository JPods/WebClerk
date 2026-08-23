from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Order, OrderLine
from apps.core.models import Contact


class OrderTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Order."""

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
        self.order.update_sell_cost_totals(persist=True)
        self.order.refresh_from_db()

        totals = self.order.totals
        self.assertEqual(totals['subtotal'], 0.0)
        self.assertEqual(totals['total'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['margin'], 0.0)
        self.assertIsNone(totals['margin_pc'])

    def test_compute_totals_with_lines(self):
        """Test computing totals with line items."""
        # Create line items
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 2'},
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        self.order.update_sell_cost_totals(persist=True)
        self.order.refresh_from_db()

        totals = self.order.totals
        # Check totals
        self.assertEqual(totals['subtotal'], 35.00)
        self.assertEqual(totals['total'], 35.00)
        self.assertEqual(totals['cost'], 28.00)
        self.assertEqual(totals['margin'], 7.00)
        self.assertAlmostEqual(totals['margin_pc'], 20.00, places=2)

    def test_compute_totals_with_discounts(self):
        """Test computing totals with discounts."""
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 100.00, 'discount_amount': 10.00, 'extended': 90.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        self.order.update_sell_cost_totals(persist=True)
        self.order.refresh_from_db()

        totals = self.order.totals
        # Check totals include discount
        self.assertEqual(totals['subtotal'], 90.00)
        self.assertEqual(totals['discount'], 10.00)
        self.assertEqual(totals['total'], 90.00)
        self.assertEqual(totals['cost'], 80.00)
        self.assertEqual(totals['margin'], 10.00)
        self.assertAlmostEqual(totals['margin_pc'], 11.11, places=2)

    def test_compute_totals_with_additional_costs(self):
        """Test computing totals with additional cost components."""
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'staged': 1, 'remaining': 1},
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

        self.order.update_sell_cost_totals(persist=True)
        self.order.refresh_from_db()

        totals = self.order.totals
        # Check totals
        self.assertEqual(totals['subtotal'], 100.00)
        self.assertEqual(totals['total'], 100.00)
        self.assertEqual(totals['cost'], 100.00)  # 80 + 5 + 2 + 3 + 4 + 6
        self.assertEqual(totals['margin'], 0.00)
        self.assertAlmostEqual(totals['margin_pc'], 0.00, places=2)
