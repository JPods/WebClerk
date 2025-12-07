import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Invoice, InvoiceLine
from apps.core.models import Contact


class InvoiceModelTest(TestCase):
    """Test cases for Invoice model."""

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
            invoice_id=invoice,
            description="Item 1",
            quantity={"placed": 2},
            price={"unit": 10.00, "extended": 20.00},
            cost={"extended": 16.00}
        )
        line2 = InvoiceLine.objects.create(
            invoice_id=invoice,
            description="Item 2",
            quantity={"placed": 1},
            price={"unit": 15.00, "extended": 15.00},
            cost={"extended": 12.00}
        )

        # Test totals calculation
        result = invoice.update_sell_cost_totals(persist=False)

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


class InvoiceLineModelTest(TestCase):
    """Test cases for InvoiceLine model."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="draft",
            customer_id=self.customer.id
        )

    def test_invoice_line_creation(self):
        """Test basic invoice line creation."""
        line = InvoiceLine.objects.create(
            invoice_id=self.invoice,
            description="Test Item",
            quantity={"placed": 5},
            price={"unit": 20.00},
            cost={"unit": 15.00}
        )

        self.assertEqual(line.invoice_id, self.invoice)
        self.assertEqual(line.description, "Test Item")
        self.assertEqual(line.quantity["placed"], 5)
        self.assertEqual(line.price["unit"], 20.00)
        self.assertEqual(line.cost["unit"], 15.00)