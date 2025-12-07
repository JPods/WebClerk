import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import PurchaseOrder, PurchaseOrderLine
from apps.core.models import Contact


class PurchaseOrderModelTest(TestCase):
    """Test cases for PurchaseOrder model."""

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

    def test_purchase_order_creation(self):
        """Test basic purchase order creation."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(po.status, "planned")
        self.assertEqual(po.customer_id, self.customer.id)
        self.assertEqual(po.vendor_id, self.vendor.id)
        self.assertIsNotNone(po.dt_created)
        self.assertIsNotNone(po.dt_modified)

    def test_purchase_order_str_method(self):
        """Test string representation of purchase order."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        expected_str = f"PurchaseOrder #{po.id} ()"
        self.assertEqual(str(po), expected_str)

    def test_purchase_order_name_property(self):
        """Test name property getter and setter."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no name fields
        self.assertEqual(po.name, "")

        # Test setter (should set _transient_name)
        po.name = "Test PO"
        self.assertEqual(po._transient_name, "Test PO")
        self.assertEqual(po.name, "Test PO")

    def test_purchase_order_po_no_property(self):
        """Test po_no property getter and setter."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Test getter with no po_no
        self.assertEqual(po.po_no, "")

        # Test setter
        po.po_no = "PO-001"
        self.assertEqual(po._transient_po_no, "PO-001")
        self.assertEqual(po.po_no, "PO-001")

    def test_purchase_order_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method without persistence."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        line1 = PurchaseOrderLine.objects.create(
            parent=po,
            description="Item 1",
            quantity={'placed': 2},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        line2 = PurchaseOrderLine.objects.create(
            parent=po,
            description="Item 2",
            quantity={'placed': 1},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        result = po.update_sell_cost_totals(persist=False)

        self.assertIn('sell', result)
        self.assertIn('cost', result)
        self.assertIn('totals', result)

        # Check sell totals (should be empty for PO)
        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['sell']['total'], 0.0)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)  # 16 + 12
        self.assertEqual(result['cost']['total'], 28.00)

        # Check totals
        self.assertEqual(result['totals']['total'], 28.00)
        self.assertEqual(result['totals']['cost'], 28.00)
        self.assertEqual(result['totals']['margin'], -28.00)

    def test_purchase_order_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        PurchaseOrderLine.objects.create(
            parent=po,
            description="Test Item",
            quantity={'placed': 1},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        result = po.update_sell_cost_totals(persist=True)

        # Refresh from database
        po.refresh_from_db()

        # Check that totals were saved
        self.assertEqual(po.sell['total'], 0.0)
        self.assertEqual(po.cost['total'], 80.00)
        self.assertEqual(po.totals['total'], 80.00)
        self.assertEqual(po.totals['cost'], 80.00)


class PurchaseOrderLineModelTest(TestCase):
    """Test cases for PurchaseOrderLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_purchase_order_line_creation(self):
        """Test basic purchase order line creation."""
        line = PurchaseOrderLine.objects.create(
            parent=self.po,
            description="Test Item",
            quantity={'placed': 5},
            cost={'unit': 15.00, 'extended': 75.00}
        )

        self.assertEqual(line.parent, self.po)
        self.assertEqual(line.description, "Test Item")
        self.assertEqual(line.quantity['placed'], 5)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_purchase_order_line_parent_ref_property(self):
        """Test parent_ref_id property."""
        line = PurchaseOrderLine.objects.create(
            parent=self.po,
            description="Test Item",
            quantity={'placed': 1}
        )

        # Test getter
        self.assertEqual(line.purchaseorder_ref_id, self.po.id)

        # Test setter
        new_po = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.purchaseorder_ref_id = new_po.id
        self.assertEqual(line.purchaseorder_id, new_po.id)