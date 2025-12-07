import pytest
from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Invoice, InvoiceLine, SalesOrder, SalesOrderLine
from apps.transactions.services.invoice_totals import compute_invoice_sell_cost_totals, _d
from apps.transactions.services.order_to_invoice import transfer_order_to_invoice
from apps.core.models import Contact


class InvoiceTotalsServiceTest(TestCase):
    """Test cases for invoice_totals service functions."""

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

    def test_compute_invoice_sell_cost_totals_empty_invoice(self):
        """Test totals computation for invoice with no lines."""
        result = compute_invoice_sell_cost_totals(self.invoice)

        # Should return default structure with zeros
        self.assertIn('sell', result)
        self.assertIn('cost', result)
        self.assertIn('totals', result)

        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['sell']['total'], 0.0)

        self.assertEqual(result['cost']['line_sum_goods'], 0.0)
        self.assertEqual(result['cost']['total'], 0.0)

        self.assertEqual(result['totals']['total'], 0.0)
        self.assertEqual(result['totals']['cost'], 0.0)
        self.assertEqual(result['totals']['margin'], 0.0)
        self.assertIsNone(result['totals']['margin_pc'])

    def test_compute_invoice_sell_cost_totals_single_line(self):
        """Test totals computation for invoice with single line item."""
        # Create a line item
        InvoiceLine.objects.create(
            invoice_id=self.invoice,
            description="Test Item",
            quantity={"placed": 2},
            price={"extended": 20.00},
            cost={"extended": 16.00, "tax": 1.60}
        )

        result = compute_invoice_sell_cost_totals(self.invoice)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 20.00)
        self.assertEqual(result['sell']['total'], 20.00)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 16.00)
        self.assertEqual(result['cost']['line_sum_tax'], 1.60)
        self.assertEqual(result['cost']['total'], 17.60)  # 16 + 1.60

        # Check margin calculations
        self.assertEqual(result['totals']['total'], 20.00)
        self.assertEqual(result['totals']['cost'], 17.60)
        self.assertEqual(result['totals']['margin'], 2.40)
        self.assertAlmostEqual(result['totals']['margin_pc'], 12.00, places=2)


class OrderToInvoiceServiceTest(TestCase):
    """Test cases for order_to_invoice service functions."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.order = SalesOrder.objects.create(
            status="fulfilled",
            customer_id=self.customer.id
        )

    def test_transfer_order_to_invoice_basic(self):
        """Test basic order to invoice transfer."""
        # Create order lines
        SalesOrderLine.objects.create(
            parent=self.order,
            description="Test Item",
            quantity={"placed": 2, "remaining": 2},
            price={"unit": 10.00, "extended": 20.00},
            cost={"extended": 16.00}
        )

        result = transfer_order_to_invoice(self.order)

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['invoice_id'])

        # Check invoice was created
        invoice = Invoice.objects.get(id=result['invoice_id'])
        self.assertEqual(invoice.status, "pending")
        self.assertEqual(invoice.refs['source']['sales_order_id'], self.order.id)

        # Check lines were transferred
        lines = InvoiceLine.objects.filter(invoice_id=invoice)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line.quantity['remaining'], 2)

    def test_transfer_order_to_invoice_partial(self):
        """Test partial order to invoice transfer."""
        # Create order lines
        SalesOrderLine.objects.create(
            parent=self.order,
            description="Item 1",
            quantity={"placed": 5, "remaining": 3},
            price={"unit": 10.00, "extended": 30.00},
            cost={"extended": 24.00}
        )
        SalesOrderLine.objects.create(
            parent=self.order,
            description="Item 2",
            quantity={"placed": 2, "remaining": 0},  # Already invoiced
            price={"unit": 5.00, "extended": 0.00},
            cost={"extended": 0.00}
        )

        result = transfer_order_to_invoice(self.order)

        self.assertTrue(result['success'])
        self.assertEqual(result['lines_transferred'], 1)  # Only one line with remaining > 0

        # Check order status updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "fulfilled")  # Since remaining total <= 0