import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.transactions.models import Cash, Invoice
from apps.core.models import Contact
from apps.orgs.models import OrgBase


class CashModelTest(TestCase):
    """Test cases for Cash model."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            company="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            company="Jane Smith",
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

    def test_cash_creation(self):
        """Test basic cash creation."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=50.00,
            gateway="stripe",
            status="pending"
        )

        self.assertEqual(cash.invoice, self.invoice)
        self.assertEqual(cash.contact_id, self.contact.pk)
        self.assertEqual(cash.amount, 50.00)
        self.assertEqual(cash.gateway, "stripe")
        self.assertEqual(cash.status, "pending")
        self.assertIsNotNone(cash.dt_created)
        self.assertIsNotNone(cash.dt_modified)

    def test_cash_str_method(self):
        """Test string representation of cash."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=75.50,
            status="completed"
        )

        expected_str = f"Cash #{cash.id} - +75.50 (completed) for Invoice #{self.invoice.id}"
        self.assertEqual(str(cash), expected_str)

    def test_cash_refs_and_metadata_defaults(self):
        """Test that refs and metadata have proper defaults."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        self.assertIsNotNone(cash.refs)
        self.assertIsNotNone(cash.metadata)
        self.assertIn('invoice_ids', cash.refs)
        self.assertIn('reconciliation', cash.metadata)

    def test_cash_add_invoice_ref(self):
        """Test adding invoice reference."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        # Initially should not have invoice in refs
        self.assertNotIn(self.invoice.id, cash.refs.get('invoice_ids', []))

        # Add ref
        cash.add_invoice_ref(self.invoice.id)
        cash.refresh_from_db()

        self.assertIn(self.invoice.id, cash.refs['invoice_ids'])

    def test_cash_add_order_ref(self):
        """Test adding order reference."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        cash.add_order_ref(123)
        cash.refresh_from_db()

        self.assertIn(123, cash.refs['order_ids'])

    def test_cash_set_source_ref(self):
        """Test setting source reference."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        cash.set_source_ref('invoice', self.invoice.id)
        cash.refresh_from_db()

        self.assertEqual(cash.refs['source']['type'], 'invoice')
        self.assertEqual(cash.refs['source']['id'], self.invoice.id)

    def test_cash_add_reconciliation_note(self):
        """Test adding reconciliation note."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        cash.add_reconciliation_note("Test reconciliation note")
        cash.refresh_from_db()

        self.assertEqual(cash.metadata['reconciliation']['notes'], "Test reconciliation note")

    def test_cash_add_audit_entry(self):
        """Test adding audit entry."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00
        )

        cash.add_audit_entry('test_action', {'key': 'value'})
        cash.save()                 # the caller saves (add_audit_entry does not)
        cash.refresh_from_db()

        audit_trail = cash.metadata['audit_trail']
        self.assertEqual(len(audit_trail), 1)
        self.assertEqual(audit_trail[0]['action'], 'test_action')
        self.assertEqual(audit_trail[0]['details']['key'], 'value')

    def test_cash_mark_as_completed(self):
        """Test marking cash as completed."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="processing"
        )

        cash.mark_as_completed()
        cash.refresh_from_db()

        self.assertEqual(cash.status, "completed")
        self.assertIsNotNone(cash.dt_processed)

    def test_cash_mark_as_failed(self):
        """Test marking cash as failed."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="processing"
        )

        cash.mark_as_failed("Gateway timeout")
        cash.refresh_from_db()

        self.assertEqual(cash.status, "failed")
        self.assertIn("Gateway timeout", cash.comments["process"][-1]["mgs"])

    def test_cash_reconcile(self):
        """Test reconciling cash."""
        cash = Cash.objects.create(
            invoice=self.invoice,
            contact_id=self.contact.pk,
            amount=25.00,
            status="completed",
            reconciled=False
        )

        cash.reconcile()
        cash.refresh_from_db()

        self.assertTrue(cash.reconciled)
        self.assertIsNotNone(cash.dt_reconciliation)


# CashMethod and Term were removed from the schema: their tables
# (cash_methods, terms) no longer exist. The method is now a CharField
# on Cash, and terms live in accounts.Term. The tests that exercised those two
# models were deleted with them rather than left importing names that are gone.
