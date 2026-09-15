import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Payment, Invoice, PaymentApplication
from apps.transactions.services.payment.payment_apply import apply_payment_to_invoice, unapply_payment_from_invoice, get_invoice_payment_status
from apps.core.models import Contact
from apps.orgs.models import OrgBase


class PaymentApplicationServiceTest(TestCase):
    """Test cases for payment application service functions."""

    def setUp(self):
        """Set up test data."""
        self.customer_org = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.vendor_org = OrgBase.objects.create(
            display_name="Jane Smith",
            org_type="vendor"
        )
        self.contact = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer_org.id,
            vendor_id=self.vendor_org.id,
            totals={'total': 100.00, 'received': 0.00, 'balance': 100.00}
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=50.00,
            status="completed"
        )

    def test_apply_payment_to_invoice_success(self):
        """Test successful payment application to invoice."""
        result = apply_payment_to_invoice(self.invoice, self.payment, 25.00)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 25.00)
        self.assertEqual(result['invoice_balance_remaining'], 75.00)
        self.assertFalse(result['payment_fully_applied'])
        self.assertFalse(result['invoice_fully_paid'])

        # Check invoice totals updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.totals['received'], 25.00)
        self.assertEqual(self.invoice.totals['balance'], 75.00)

        # Check payment refs updated
        self.payment.refresh_from_db()
        self.assertIn(self.invoice.id, self.payment.refs['invoice_ids'])

        # Check audit entry added
        audit_trail = self.payment.metadata['audit_trail']
        self.assertEqual(len(audit_trail), 1)
        self.assertEqual(audit_trail[0]['action'], 'payment_applied')

    def test_apply_payment_to_invoice_full_payment(self):
        """Test applying full payment amount."""
        result = apply_payment_to_invoice(self.invoice, self.payment)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 50.00)
        self.assertEqual(result['invoice_balance_remaining'], 50.00)
        self.assertTrue(result['payment_fully_applied'])
        self.assertFalse(result['invoice_fully_paid'])

        # Check payment status updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'fully_applied')

    def test_apply_payment_to_invoice_full_invoice_payment(self):
        """Test applying payment that fully pays the invoice."""
        small_payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=100.00,
            status="completed"
        )

        result = apply_payment_to_invoice(self.invoice, small_payment)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 100.00)
        self.assertEqual(result['invoice_balance_remaining'], 0.00)
        self.assertTrue(result['payment_fully_applied'])
        self.assertTrue(result['invoice_fully_paid'])

        # Check invoice status updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_apply_payment_to_invoice_pending_payment(self):
        """Test applying payment that is not completed."""
        pending_payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="pending"
        )

        with self.assertRaises(Exception) as cm:
            apply_payment_to_invoice(self.invoice, pending_payment)

        self.assertIn("Payment must be completed", str(cm.exception))

    def test_apply_payment_to_invoice_invalid_status(self):
        """Test applying payment to invoice with invalid status."""
        self.invoice.status = 'paid'
        self.invoice.save()

        with self.assertRaises(Exception) as cm:
            apply_payment_to_invoice(self.invoice, self.payment)

        self.assertIn("does not allow payment application", str(cm.exception))

    def test_unapply_payment_from_invoice(self):
        """Test removing payment application from invoice."""
        # First apply payment
        apply_payment_to_invoice(self.invoice, self.payment, 25.00)

        # Get the application
        application = PaymentApplication.objects.get(
            payment=self.payment,
            invoice=self.invoice
        )

        # Unapply
        result = unapply_payment_from_invoice(self.payment, self.invoice)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_unapplied'], 25.00)

        # Check invoice totals reverted
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.totals['received'], 0.00)
        self.assertEqual(self.invoice.totals['balance'], 100.00)

        # Check application deleted
        with self.assertRaises(PaymentApplication.DoesNotExist):
            PaymentApplication.objects.get(id=application.id)

    def test_get_invoice_payment_status(self):
        """Test getting comprehensive payment status for invoice."""
        # Apply some payments
        payment1 = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=30.00,
            status="completed"
        )
        payment2 = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=20.00,
            status="completed"
        )

        apply_payment_to_invoice(self.invoice, payment1, 30.00)
        apply_payment_to_invoice(self.invoice, payment2, 20.00)

        status = get_invoice_payment_status(self.invoice)

        self.assertEqual(status['total_due'], 100.00)
        self.assertEqual(status['total_paid'], 50.00)
        self.assertEqual(status['balance'], 50.00)
        self.assertEqual(status['payment_count'], 2)
        self.assertFalse(status['is_fully_paid'])
        self.assertEqual(len(status['payments']), 2)
