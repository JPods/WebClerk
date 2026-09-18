"""Tests for GL journal posting from staged metadata.

Validates that invoice and cash saves produce actual GlJournal records
from the staged metadata.gl_accounts postings, with correct debit/credit
amounts, double-posting guards, and balance verification.
"""
import pytest
from decimal import Decimal

from tests.conftest import InvoiceFactory, CustomerFactory, ContactFactory


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
class TestPostStagedGlEntries:
    """Test the post_staged_gl_entries() function directly."""

    def test_creates_entries_from_staged_metadata(self):
        """Staged postings in metadata.gl_accounts → GlJournal records."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = InvoiceFactory()
        invoice.metadata = invoice.metadata or {}
        invoice.metadata['gl_accounts'] = {
            'event': 'invoice_created',
            'postings': [
                {'side': 'debit', 'purpose': 'accounts_receivable', 'account': '1100-accounts_receivable', 'amount': 500.0},
                {'side': 'credit', 'purpose': 'sales_revenue', 'account': '4000-sales_revenue', 'amount': 500.0},
            ],
        }
        invoice.__class__.objects.filter(pk=invoice.pk).update(metadata=invoice.metadata)
        invoice.refresh_from_db()

        count = post_staged_gl_entries(invoice)

        assert count == 2
        entries = list(GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice'))
        assert len(entries) == 2

        debit_entry = next(e for e in entries if e.debit)
        credit_entry = next(e for e in entries if e.credit)

        assert debit_entry.account == '1100-accounts_receivable'
        assert debit_entry.debit == 500.0
        assert debit_entry.credit is None
        assert debit_entry.source == 'automation'
        assert debit_entry.type == 'sales'

        assert credit_entry.account == '4000-sales_revenue'
        assert credit_entry.credit == 500.0
        assert credit_entry.debit is None

    def test_no_double_posting(self):
        """Calling post_staged_gl_entries twice does not duplicate entries."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = InvoiceFactory()
        invoice.metadata = invoice.metadata or {}
        invoice.metadata['gl_accounts'] = {
            'event': 'invoice_created',
            'postings': [
                {'side': 'debit', 'account': '1100-accounts_receivable', 'amount': 100.0},
                {'side': 'credit', 'account': '4000-sales_revenue', 'amount': 100.0},
            ],
        }
        invoice.__class__.objects.filter(pk=invoice.pk).update(metadata=invoice.metadata)
        invoice.refresh_from_db()

        count1 = post_staged_gl_entries(invoice)
        count2 = post_staged_gl_entries(invoice)

        assert count1 == 2
        assert count2 == 0  # blocked by duplicate guard
        assert GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice').count() == 2

    def test_gl_entries_balance(self):
        """Sum of debits must equal sum of credits for each source."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal
        from django.db.models import Sum

        invoice = InvoiceFactory()
        invoice.metadata = invoice.metadata or {}
        invoice.metadata['gl_accounts'] = {
            'event': 'invoice_created',
            'postings': [
                {'side': 'debit', 'account': '1100-accounts_receivable', 'amount': 750.0},
                {'side': 'credit', 'account': '4000-sales_revenue', 'amount': 750.0},
            ],
        }
        invoice.__class__.objects.filter(pk=invoice.pk).update(metadata=invoice.metadata)
        invoice.refresh_from_db()
        post_staged_gl_entries(invoice)

        totals = GlJournal.objects.filter(
            source_id=invoice.pk, source_model='invoice'
        ).aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))

        assert totals['total_debit'] == totals['total_credit']

    def test_zero_amount_skipped(self):
        """Postings with amount=0 are not created as GL entries."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = InvoiceFactory()
        invoice.metadata = invoice.metadata or {}
        invoice.metadata['gl_accounts'] = {
            'event': 'invoice_created',
            'postings': [
                {'side': 'debit', 'account': '1100-accounts_receivable', 'amount': 0},
                {'side': 'credit', 'account': '4000-sales_revenue', 'amount': 0},
            ],
        }
        invoice.__class__.objects.filter(pk=invoice.pk).update(metadata=invoice.metadata)
        invoice.refresh_from_db()

        count = post_staged_gl_entries(invoice)
        assert count == 0
        assert GlJournal.objects.filter(source_id=invoice.pk).count() == 0

    def test_no_metadata_returns_zero(self):
        """Instance with no metadata.gl_accounts returns 0."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries

        invoice = InvoiceFactory()
        count = post_staged_gl_entries(invoice)
        assert count == 0

    def test_cash_gl_entries_type(self):
        """Cash postings get type='general' not 'sales'."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal
        from apps.transactions.models import Cash
        from django.utils import timezone

        from apps.core.models import Contact
        contact = Contact.objects.create(
            email='payer@test.com',
            name_first='Test', name_last='Payer',
        )
        invoice = InvoiceFactory()
        cash = Cash.objects.create(
            amount=200.0,
            status='completed',
            contact_id=contact.pk,
            invoice=invoice,
            dt_cash=timezone.now(),
        )
        cash.metadata = cash.metadata or {}
        cash.metadata['gl_accounts'] = {
            'event': 'cash_received',
            'postings': [
                {'side': 'debit', 'purpose': 'cash_receipt', 'account': '1000-cash', 'amount': 200.0},
                {'side': 'credit', 'purpose': 'accounts_receivable', 'account': '1100-accounts_receivable', 'amount': 200.0},
            ],
        }
        cash.__class__.objects.filter(pk=cash.pk).update(metadata=cash.metadata)
        cash.refresh_from_db()

        count = post_staged_gl_entries(cash)
        assert count == 2

        entries = GlJournal.objects.filter(source_id=cash.pk, source_model='cash')
        for entry in entries:
            assert entry.type == 'general'
            assert entry.source == 'automation'
