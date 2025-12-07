import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import SalesOrder, SalesOrderLine
from apps.core.models import Contact


class SalesOrderModelTest(TestCase):
    """Test cases for SalesOrder model."""

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

    def test_sales_order_creation(self):
        """Test basic sales order creation."""
        sales_order = SalesOrder.objects.create(
            ida="SO-001",
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(sales_order.ida, "SO-001")
        self.assertEqual(sales_order.status, "planned")
        self.assertEqual(sales_order.customer_id, self.customer.id)
        self.assertEqual(sales_order.vendor_id, self.vendor.id)
        self.assertIsNotNone(sales_order.dt_created)
        self.assertIsNotNone(sales_order.dt_modified)

    def test_sales_order_str_method(self):
        """Test string representation of sales order."""
        sales_order = SalesOrder.objects.create(
            ida="SO-001",
            status="planned",
            customer_id=self.customer.id
        )

        expected_str = "SO-001"
        self.assertEqual(str(sales_order), expected_str)

    def test_sales_order_name_property(self):
        """Test name property getter and setter."""
        sales_order = SalesOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no name fields
        self.assertEqual(sales_order.name, "")

        # Test setter (should set _transient_order_no)
        sales_order.name = "Test Order"
        self.assertEqual(sales_order._transient_order_no, "Test Order")
        self.assertEqual(sales_order.name, "Test Order")

    def test_sales_order_status_choices(self):
        """Test that status choices are properly defined."""
        expected_choices = [
            ('planned', 'Planned'),
            ('released', 'Released'),
            ('in_progress', 'In Progress'),
            ('hold', 'Hold'),
            ('complete', 'Complete'),
            ('canceled', 'Canceled'),
        ]

        self.assertEqual(SalesOrder.STATUS_CHOICES, expected_choices)

    def test_sales_order_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method without persistence."""
        sales_order = SalesOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        line1 = SalesOrderLine.objects.create(
            parent=sales_order,
            description="Item 1",
            quantity={'placed': 2, 'remaining': 2},
            price={'unit': 10.00, 'extended': 20.00},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        line2 = SalesOrderLine.objects.create(
            parent=sales_order,
            description="Item 2",
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 15.00, 'extended': 15.00},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        result = sales_order.update_sell_cost_totals(persist=False)

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

    def test_sales_order_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        sales_order = SalesOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        SalesOrderLine.objects.create(
            parent=sales_order,
            description="Test Item",
            quantity={'placed': 1, 'remaining': 1},
            price={'unit': 100.00, 'extended': 100.00},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        result = sales_order.update_sell_cost_totals(persist=True)

        # Refresh from database
        sales_order.refresh_from_db()

        # Check that totals were saved
        self.assertEqual(sales_order.sell['total'], 100.00)
        self.assertEqual(sales_order.cost['total'], 80.00)
        self.assertEqual(sales_order.totals['total'], 100.00)
        self.assertEqual(sales_order.totals['cost'], 80.00)
        self.assertEqual(sales_order.totals['margin'], 20.00)


class SalesOrderLineModelTest(TestCase):
    """Test cases for SalesOrderLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.sales_order = SalesOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_sales_order_line_creation(self):
        """Test basic sales order line creation."""
        line = SalesOrderLine.objects.create(
            parent=self.sales_order,
            description="Test Item",
            quantity={'placed': 5, 'remaining': 5},
            price={'unit': 20.00},
            cost={'unit': 15.00}
        )

        self.assertEqual(line.parent, self.sales_order)
        self.assertEqual(line.description, "Test Item")
        self.assertEqual(line.quantity['placed'], 5)
        self.assertEqual(line.price['unit'], 20.00)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_sales_order_line_parent_ref_property(self):
        """Test parent_ref_id property."""
        line = SalesOrderLine.objects.create(
            parent=self.sales_order,
            description="Test Item",
            quantity={'placed': 1, 'remaining': 1}
        )

        # Test getter
        self.assertEqual(line.salesorder_ref_id, self.sales_order.id)

        # Test setter
        new_sales_order = SalesOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.salesorder_ref_id = new_sales_order.id
        self.assertEqual(line.parent_id, new_sales_order.id)