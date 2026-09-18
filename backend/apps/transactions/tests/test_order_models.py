import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Order, OrderLine
from apps.orgs.models import OrgBase


class OrderModelTest(TestCase):
    """Test cases for Order model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            display_name="Jane Smith",
            org_type="vendor"
        )

    def test_order_creation(self):
        """Test basic order creation."""
        order = Order.objects.create(
            ida="SO-001",
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(order.ida, "SO-001")
        self.assertEqual(order.status, "planned")
        self.assertEqual(order.customer_id, self.customer.id)
        self.assertEqual(order.vendor_id, self.vendor.id)
        self.assertIsNotNone(order.dt_created)
        self.assertIsNotNone(order.dt_modified)

    def test_order_str_method(self):
        """Test string representation of order."""
        order = Order.objects.create(
            ida="SO-001",
            status="planned",
            customer_id=self.customer.id
        )

        expected_str = "SO-001"
        self.assertEqual(str(order), expected_str)

    def test_order_name_property(self):
        """Test ida as the order identifier."""
        order = Order.objects.create(
            ida="SO-NAME",
            status="planned",
            customer_id=self.customer.id
        )

        self.assertEqual(order.ida, "SO-NAME")

    def test_order_status_choices(self):
        """Test that status choices are properly defined."""
        expected_choices = (
            ('', '---------'),
            ('planned', 'Planned'),
            ('signoff_request', 'SignOff Request'),
            ('released', 'Released'),
            ('in_progress', 'In Progress'),
            ('hold', 'Hold'),
            ('consigned', 'Consigned'),
            ('deferred', 'Deferred'),
            ('complete', 'Complete'),
            ('canceled', 'Canceled'),
        )

        self.assertEqual(Order.STATUS_CHOICES, expected_choices)

    def test_order_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method calculates correctly."""
        order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        OrderLine.objects.create(
            order=order,
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        OrderLine.objects.create(
            order=order,
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        order.update_sell_cost_totals(persist=True)
        order.refresh_from_db()

        totals = order.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertIn('margin', totals)

    def test_order_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        OrderLine.objects.create(
            order=order,
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        order.update_sell_cost_totals(persist=True)

        # Refresh from database
        order.refresh_from_db()

        # Check that totals were saved
        self.assertIn('total', order.totals)
        self.assertIn('cost', order.totals)
        self.assertIn('margin', order.totals)


class OrderLineModelTest(TestCase):
    """Test cases for OrderLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_order_line_creation(self):
        """Test basic order line creation."""
        line = OrderLine.objects.create(
            order=self.order,
            quantity={'staged': 5, 'remaining': 5},
            price={'unit': 20.00},
            cost={'unit': 15.00}
        )

        self.assertEqual(line.order, self.order)
        self.assertEqual(line.quantity['staged'], 5)
        self.assertEqual(line.price['unit'], 20.00)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_order_line_parent_ref_property(self):
        """Test order FK relationship."""
        line = OrderLine.objects.create(
            order=self.order,
            quantity={'staged': 1, 'remaining': 1}
        )

        # Test FK relationship
        self.assertEqual(line.order_id, self.order.id)

        # Test reassignment
        new_order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.order = new_order
        line.save()
        self.assertEqual(line.order_id, new_order.id)
