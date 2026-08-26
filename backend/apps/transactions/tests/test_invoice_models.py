import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Invoice, InvoiceLine
from apps.orgs.models import OrgBase


class InvoiceModelTest(TestCase):
    """Test cases for Invoice model."""

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

    def test_invoice_creation(self):
        """Test basic invoice creation."""
        invoice = Invoice.objects.create(
            ida="INV-001",
            status="draft",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id,
            refs={"order_id": 123},
            metadata={"payment_history": []}
        )

        self.assertEqual(invoice.ida, "INV-001")
        self.assertEqual(invoice.status, "draft")
        self.assertEqual(invoice.customer_id, self.customer.id)
        self.assertEqual(invoice.vendor_id, self.vendor.id)
        self.assertEqual(invoice.refs["order_id"], 123)
        self.assertIsNotNone(invoice.dt_created)
        self.assertIsNotNone(invoice.dt_modified)

    def test_invoice_str_method(self):
        """Test string representation of invoice."""
        invoice = Invoice.objects.create(
            ida="INV-001",
            status="draft",
            customer_id=self.customer.id
        )

        expected_str = f"Invoice #{invoice.id} (INV-001)"
        self.assertEqual(str(invoice), expected_str)

    def test_invoice_update_sell_cost_totals_without_persist(self):
        """Test update_sell_cost_totals method without persistence."""
        invoice = Invoice.objects.create(
            status="draft",
            customer_id=self.customer.id
        )

        # Create some line items
        line1 = InvoiceLine.objects.create(
            invoice=invoice,
            quantity={"staged": 2},
            price={"unit": 10.00, "extended": 20.00},
            cost={"extended": 16.00}
        )
        line2 = InvoiceLine.objects.create(
            invoice=invoice,
            quantity={"staged": 1},
            price={"unit": 15.00, "extended": 15.00},
            cost={"extended": 12.00}
        )

        # Test totals calculation
        invoice.update_sell_cost_totals(persist=True)
        invoice.refresh_from_db()

        totals = invoice.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertIn('margin', totals)


class InvoiceLineModelTest(TestCase):
    """Test cases for InvoiceLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.invoice = Invoice.objects.create(
            status="draft",
            customer_id=self.customer.id
        )

    def test_invoice_line_creation(self):
        """Test basic invoice line creation."""
        line = InvoiceLine.objects.create(
            invoice=self.invoice,
            quantity={"staged": 5},
            price={"unit": 20.00},
            cost={"unit": 15.00}
        )

        self.assertEqual(line.invoice, self.invoice)
        self.assertEqual(line.quantity["staged"], 5)
        self.assertEqual(line.price["unit"], 20.00)
        self.assertEqual(line.cost["unit"], 15.00)
