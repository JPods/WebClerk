import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Order, OrderLine
from apps.core.models import Contact


class OrderModelTest(TestCase):
    """Test cases for Order model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.vendor = Contact.objects.create(
            name_first="Jane",
            name_last="Smith",
            email="jane.smith@example.com"
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
        """Test name property getter and setter."""
        order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no name fields
        self.assertEqual(order.name, "")

        # Test setter (should set _transient_order_no)
        order.name = "Test Order"
        self.assertEqual(order._transient_order_no, "Test Order")
        self.assertEqual(order.name, "Test Order")

    def test_order_status_choices(self):
        """Test that status choices are properly defined."""
        expected_choices = [
            ('planned', 'Planned'),
            ('released', 'Released'),
            ('in_progress', 'In Progress'),
            ('hold', 'Hold'),
            ('complete', 'Complete'),
            ('canceled', 'Canceled'),
        ]

        self.assertEqual(Order.STATUS_CHOICES, expected_choices)

    def test_order_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method without persistence."""
        order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        line1 = OrderLine.objects.create(
            parent=order,
            description="Item 1",
            quantity={'staged': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        line2 = OrderLine.objects.create(
            parent=order,
            description="Item 2",
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        result = order.update_sell_cost_totals(persist=False)

        self.assertIn('sell', result)
        self.assertIn('cost', result)
        self.assertIn('totals', result)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 35.00)  # 20 + 15
        self.assertEqual(result['sell']['total'], 35.00)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)  # 16 + 12
        self.assertEqual(result['cost']['total'], 28.00)

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 35.00)
        self.assertEqual(result['totals']['cost'], 28.00)
        self.assertEqual(result['totals']['margin'], 7.00)
        self.assertAlmostEqual(result['totals']['margin_pc'], 20.00, places=2)

    def test_order_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        OrderLine.objects.create(
            parent=order,
            description="Test Item",
            quantity={'staged': 1, 'remaining': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        result = order.update_sell_cost_totals(persist=True)

        # Refresh from database
        order.refresh_from_db()

        # Check that totals were saved
        self.assertEqual(order.sell['total'], 100.00)
        self.assertEqual(order.cost['total'], 80.00)
        self.assertEqual(order.totals['total'], 100.00)
        self.assertEqual(order.totals['cost'], 80.00)
        self.assertEqual(order.totals['margin'], 20.00)


class OrderLineModelTest(TestCase):
    """Test cases for OrderLine model."""

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

    def test_order_line_creation(self):
        """Test basic order line creation."""
        line = OrderLine.objects.create(
            parent=self.order,
            description="Test Item",
            quantity={'staged': 5, 'remaining': 5},
            price={'unit': 20.00},
            cost={'unit': 15.00}
        )

        self.assertEqual(line.parent, self.order)
        self.assertEqual(line.description, "Test Item")
        self.assertEqual(line.quantity['staged'], 5)
        self.assertEqual(line.price['unit'], 20.00)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_order_line_parent_ref_property(self):
        """Test parent_ref_id property."""
        line = OrderLine.objects.create(
            parent=self.order,
            description="Test Item",
            quantity={'staged': 1, 'remaining': 1}
        )

        # Test getter
        self.assertEqual(line.order_ref_id, self.order.id)

        # Test setter
        new_order = Order.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.order_ref_id = new_order.id
        self.assertEqual(line.parent_id, new_order.id)
