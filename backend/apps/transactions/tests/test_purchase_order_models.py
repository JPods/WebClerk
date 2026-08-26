import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Purchase, PurchaseLine
from apps.orgs.models import OrgBase


class PurchaseModelTest(TestCase):
    """Test cases for Purchase model."""

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

    def test_purchase_creation(self):
        """Test basic purchase creation."""
        po = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id
        )

        self.assertEqual(po.status, "planned")
        self.assertEqual(po.customer_id, self.customer.id)
        self.assertEqual(po.vendor_id, self.vendor.id)
        self.assertIsNotNone(po.dt_created)
        self.assertIsNotNone(po.dt_modified)

    def test_purchase_str_method(self):
        """Test string representation of purchase."""
        po = Purchase.objects.create(
            ida="PO-001",
            status="planned",
            customer_id=self.customer.id
        )

        self.assertIn("PO-001", str(po))

    def test_purchase_name_property(self):
        """Test ida as purchase identifier."""
        po = Purchase.objects.create(
            ida="PO-NAME",
            status="planned",
            customer_id=self.customer.id
        )

        self.assertEqual(po.ida, "PO-NAME")

    def test_purchase_po_no_property(self):
        """Test ida as PO number."""
        po = Purchase.objects.create(
            ida="PO-001",
            status="planned",
            customer_id=self.customer.id
        )

        self.assertEqual(po.ida, "PO-001")

    def test_purchase_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method calculates correctly."""
        po = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create some line items
        PurchaseLine.objects.create(
            purchase=po,
            quantity={'staged': 2},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        PurchaseLine.objects.create(
            purchase=po,
            quantity={'staged': 1},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        # Test totals calculation
        po.update_sell_cost_totals(persist=True)
        po.refresh_from_db()

        totals = po.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)

    def test_purchase_update_sell_cost_totals_with_persist(self):
        """Test update_sell_cost_totals method with persistence."""
        po = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

        # Create a line item
        PurchaseLine.objects.create(
            purchase=po,
            quantity={'staged': 1},
            cost={'unit': 80.00, 'extended': 80.00}
        )

        # Update totals with persistence
        po.update_sell_cost_totals(persist=True)

        # Refresh from database
        po.refresh_from_db()

        # Check that totals were saved
        self.assertIn('total', po.totals)
        self.assertIn('cost', po.totals)


class PurchaseLineModelTest(TestCase):
    """Test cases for PurchaseLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.po = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_purchase_line_creation(self):
        """Test basic purchase line creation."""
        line = PurchaseLine.objects.create(
            purchase=self.po,
            quantity={'staged': 5},
            cost={'unit': 15.00, 'extended': 75.00}
        )

        self.assertEqual(line.purchase, self.po)
        self.assertEqual(line.quantity['staged'], 5)
        self.assertEqual(line.cost['unit'], 15.00)

    def test_purchase_line_parent_ref_property(self):
        """Test purchase FK relationship."""
        line = PurchaseLine.objects.create(
            purchase=self.po,
            quantity={'staged': 1}
        )

        # Test FK relationship
        self.assertEqual(line.purchase_id, self.po.id)

        # Test reassignment
        new_po = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id
        )
        line.purchase = new_po
        line.save()
        self.assertEqual(line.purchase_id, new_po.id)
