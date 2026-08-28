import pytest
from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine
from apps.transactions.services.pricing.totals_compute import _d
from apps.transactions.services.convert.convert_order_to_invoice import transfer_order_to_invoice
from apps.orgs.models import OrgBase


class InvoiceTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Invoice."""

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

    def test_totals_empty_invoice(self):
        """Test totals computation for invoice with no lines."""
        self.invoice.update_sell_cost_totals(persist=True)
        self.invoice.refresh_from_db()

        totals = self.invoice.totals
        self.assertEqual(totals['subtotal'], 0.0)
        self.assertEqual(totals['total'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['margin'], 0.0)

    def test_totals_single_line(self):
        """Test totals computation for invoice with single line item."""
        InvoiceLine.objects.create(
            invoice=self.invoice,
            item={"description": "Test Item"},
            quantity={"staged": 2, "remaining": 2},
            price={"unit": 10.00, "extended": 20.00},
            cost={"unit": 8.00, "extended": 16.00}
        )

        self.invoice.update_sell_cost_totals(persist=True)
        self.invoice.refresh_from_db()

        totals = self.invoice.totals
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)
        self.assertGreater(totals['total'], 0)


class OrderToInvoiceServiceTest(TestCase):
    """Test cases for order_to_invoice service functions."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.order = Order.objects.create(
            status="fulfilled",
            customer_id=self.customer.id
        )

    def test_transfer_order_to_invoice_basic(self):
        """Test basic order to invoice transfer."""
        # Create order lines
        OrderLine.objects.create(
            order=self.order,
            item={"description": "Test Item"},
            quantity={"staged": 2, "active": 2},
            price={"unit": 10.00, "extended": 20.00},
            cost={"extended": 16.00}
        )

        result = transfer_order_to_invoice(self.order)

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['invoice_id'])

        # Check invoice was created
        invoice = Invoice.objects.get(id=result['invoice_id'])
        self.assertEqual(invoice.status, "pending")
        self.assertEqual(invoice.refs['source']['original_id'], self.order.id)

        # Lines are returned for React, not saved server-side
        self.assertEqual(result['lines_for_review'], 1)
        self.assertEqual(len(result['lines']), 1)
        self.assertEqual(result['lines'][0]['quantity']['active'], 2)

    def test_transfer_order_to_invoice_partial(self):
        """Test partial order to invoice transfer."""
        # Create order lines
        OrderLine.objects.create(
            order=self.order,
            item={"description": "Item 1"},
            quantity={"staged": 5, "active": 5},
            price={"unit": 10.00, "extended": 30.00},
            cost={"extended": 24.00}
        )
        ol2 = OrderLine.objects.create(
            order=self.order,
            item={"description": "Item 2"},
            quantity={"staged": 2, "active": 2, "is_complete": True},  # Already invoiced
            price={"unit": 5.00, "extended": 0.00},
            cost={"extended": 0.00}
        )

        result = transfer_order_to_invoice(self.order)

        self.assertTrue(result['success'])
        # is_complete forces remaining=0, so only one line transferred
        self.assertEqual(result['lines_for_review'], 1)
