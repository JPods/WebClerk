import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Payment, PaymentMethod, PaymentTerm, Invoice
from apps.core.models import Contact
from apps.orgs.models import OrgBase


class PaymentModelTest(TestCase):
    """Test cases for Payment model."""

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
        self.contact = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id,
            totals={'total': 100.00, 'received': 0.00, 'balance': 100.00}
        )
        self.payment_method = PaymentMethod.objects.create(
            name="Credit Card",
            description="Credit card payment"
        )
        self.payment_term = PaymentTerm.objects.create(
            name="Net 30",
            description="Payment due in 30 days",
            days=30
        )

    def test_payment_creation(self):
        """Test basic payment creation."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=50.00,
            gateway="stripe",
            status="pending"
        )

        self.assertEqual(payment.invoice, self.invoice)
        self.assertEqual(payment.contact_id, self.contact.pk)
        self.assertEqual(payment.amount, 50.00)
        self.assertEqual(payment.gateway, "stripe")
        self.assertEqual(payment.status, "pending")
        self.assertIsNotNone(payment.dt_created)
        self.assertIsNotNone(payment.dt_modified)

    def test_payment_str_method(self):
        """Test string representation of payment."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=75.50,
            status="completed"
        )

        expected_str = f"Payment #{payment.id} - +75.50 (completed) for Invoice #{self.invoice.id}"
        self.assertEqual(str(payment), expected_str)

    def test_payment_refs_and_metadata_defaults(self):
        """Test that refs and metadata have proper defaults."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        self.assertIsNotNone(payment.refs)
        self.assertIsNotNone(payment.metadata)
        self.assertIn('invoice_ids', payment.refs)
        self.assertIn('reconciliation', payment.metadata)

    def test_payment_add_invoice_ref(self):
        """Test adding invoice reference."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        # Initially should not have invoice in refs
        self.assertNotIn(self.invoice.id, payment.refs.get('invoice_ids', []))

        # Add ref
        payment.add_invoice_ref(self.invoice.id)
        payment.refresh_from_db()

        self.assertIn(self.invoice.id, payment.refs['invoice_ids'])

    def test_payment_add_order_ref(self):
        """Test adding order reference."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        payment.add_order_ref(123)
        payment.refresh_from_db()

        self.assertIn(123, payment.refs['order_ids'])

    def test_payment_set_source_ref(self):
        """Test setting source reference."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        payment.set_source_ref('invoice', self.invoice.id)
        payment.refresh_from_db()

        self.assertEqual(payment.refs['source']['type'], 'invoice')
        self.assertEqual(payment.refs['source']['id'], self.invoice.id)

    def test_payment_add_reconciliation_note(self):
        """Test adding reconciliation note."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        payment.add_reconciliation_note("Test reconciliation note")
        payment.refresh_from_db()

        self.assertEqual(payment.metadata['reconciliation']['notes'], "Test reconciliation note")

    def test_payment_add_audit_entry(self):
        """Test adding audit entry."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        payment.add_audit_entry('test_action', {'key': 'value'})
        payment.refresh_from_db()

        audit_trail = payment.metadata['audit_trail']
        self.assertEqual(len(audit_trail), 1)
        self.assertEqual(audit_trail[0]['action'], 'test_action')
        self.assertEqual(audit_trail[0]['details']['key'], 'value')

    def test_payment_mark_as_completed(self):
        """Test marking payment as completed."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="processing"
        )

        payment.mark_as_completed()
        payment.refresh_from_db()

        self.assertEqual(payment.status, "completed")
        self.assertIsNotNone(payment.dt_processed)

    def test_payment_mark_as_failed(self):
        """Test marking payment as failed."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="processing"
        )

        payment.mark_as_failed("Gateway timeout")
        payment.refresh_from_db()

        self.assertEqual(payment.status, "failed")
        self.assertIn("Gateway timeout", payment.notes)

    def test_payment_reconcile(self):
        """Test reconciling payment."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="completed",
            reconciled=False
        )

        payment.reconcile()
        payment.refresh_from_db()

        self.assertTrue(payment.reconciled)
        self.assertIsNotNone(payment.dt_reconciliation)


class PaymentMethodModelTest(TestCase):
    """Test cases for PaymentMethod model."""

    def test_payment_method_creation(self):
        """Test basic payment method creation."""
        method = PaymentMethod.objects.create(
            name="Bank Transfer",
            description="Direct bank transfer"
        )

        self.assertEqual(method.name, "Bank Transfer")
        self.assertEqual(method.description, "Direct bank transfer")
        self.assertTrue(method.is_active)

    def test_payment_method_str_method(self):
        """Test string representation of payment method."""
        method = PaymentMethod.objects.create(
            name="Check",
            description="Paper check"
        )

        self.assertEqual(str(method), "Check")


class PaymentTermModelTest(TestCase):
    """Test cases for PaymentTerm model."""

    def test_payment_term_creation(self):
        """Test basic payment term creation."""
        term = PaymentTerm.objects.create(
            name="Net 15",
            description="Payment due in 15 days",
            days=15
        )

        self.assertEqual(term.name, "Net 15")
        self.assertEqual(term.description, "Payment due in 15 days")
        self.assertEqual(term.days, 15)
        self.assertTrue(term.is_active)

    def test_payment_term_str_method(self):
        """Test string representation of payment term."""
        term = PaymentTerm.objects.create(
            name="COD",
            description="Cash on delivery",
            days=0
        )

        self.assertEqual(str(term), "COD")