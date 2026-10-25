"""Tests for GL journal posting.

One GL engine (2026-09-19): "Post to GL" posts an invoice or a cash entry through
journalize_invoice / journalize_cash, from the record's own lines and totals. The
staged metadata.gl_accounts is a preview only and is never posted. These tests build
real invoices with lines, as a user would.
"""
import pytest
from decimal import Decimal

from tests.conftest import InvoiceFactory


def invoice_with_line(unit=500.0, qty=1, unit_cost=0.0):
    """An invoice a user could have made: one line, no tax, no shipping."""
    from apps.transactions.models import InvoiceLine
    invoice = InvoiceFactory()
    InvoiceLine.objects.create(
        invoice=invoice, quantity={'active': qty},
        price={'unit': unit, 'precision': 2}, cost={'unit': unit_cost},
    )
    invoice.refresh_from_db()
    return invoice


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
class TestPostStagedGlEntries:
    """post_staged_gl_entries() — the one engine, posting from the record."""

    def test_creates_entries_from_the_invoice(self):
        """An invoice's own lines and totals → GlJournal records."""
        from apps.accounts.services.chart import role_account
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(500.0)
        count = post_staged_gl_entries(invoice)

        assert count == 2
        entries = list(GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice'))
        assert len(entries) == 2

        debit_entry = next(e for e in entries if e.debit)
        credit_entry = next(e for e in entries if e.credit)

        assert debit_entry.account == role_account('accounts_receivable')
        assert debit_entry.debit == 500.0
        assert debit_entry.credit is None
        assert debit_entry.source == 'automation'
        assert debit_entry.type == 'sales'

        assert credit_entry.account == role_account('sales_revenue')
        assert credit_entry.credit == 500.0
        assert credit_entry.debit is None

    def test_no_double_posting(self):
        """Calling post_staged_gl_entries twice does not duplicate entries."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(100.0)
        count1 = post_staged_gl_entries(invoice)
        count2 = post_staged_gl_entries(invoice)

        assert count1 == 2
        assert count2 == 0  # blocked by the already-journalized guard
        assert GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice').count() == 2

    def test_gl_entries_balance(self):
        """Sum of debits must equal sum of credits for each source."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal
        from django.db.models import Sum

        invoice = invoice_with_line(750.0, unit_cost=300.0)
        post_staged_gl_entries(invoice)

        totals = GlJournal.objects.filter(
            source_id=invoice.pk, source_model='invoice'
        ).aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))

        assert totals['total_debit'] == totals['total_credit']

    def test_zero_amount_skipped(self):
        """A line worth nothing posts nothing."""
        from apps.accounts.services.ledger_balance import post_staged_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(0.0)
        count = post_staged_gl_entries(invoice)
        assert count == 0
        assert GlJournal.objects.filter(source_id=invoice.pk).count() == 0

    def test_invoice_without_lines_returns_zero(self):
        """An invoice with no lines has nothing to post."""
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
        invoice = invoice_with_line(200.0)
        cash = Cash.objects.create(
            amount=200.0,
            status='completed',
            contact_id=contact.pk,
            invoice=invoice,
            dt_cash=timezone.now(),
        )

        count = post_staged_gl_entries(cash)
        assert count == 2

        entries = GlJournal.objects.filter(source_id=cash.pk, source_model='cash')
        for entry in entries:
            assert entry.type == 'general'
            assert entry.source == 'automation'


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
def test_tax_posts_to_the_account_its_jurisdiction_names():
    """The tax payable account is read from the jurisdiction the invoice names, never from
    a copy on the invoice (wc3, 2026-10-25): an account renamed in the chart reaches every
    invoice, and the screen has no account to send."""
    from apps.accounts.models import GlJournal
    from apps.accounts.models.tax_jurisdiction import TaxJurisdiction
    from apps.accounts.services.chart import role_account
    from apps.accounts.services.ledger_balance import post_staged_gl_entries
    from apps.transactions.models import InvoiceLine

    own_account = role_account('other_income')        # any account the chart holds
    tj = TaxJurisdiction.objects.create(tax_name='Testland', tax_rate_sales=10.0,
                                        gl_account_payable=own_account, is_active=True)
    invoice = InvoiceFactory()
    invoice.finance = {'sales_tax_id': tj.pk, 'sales_tax_rate': 10.0}
    invoice.save()
    InvoiceLine.objects.create(invoice=invoice, quantity={'active': 1},
                               price={'unit': 100.0, 'precision': 2}, cost={'unit': 0})
    invoice.refresh_from_db()
    assert float((invoice.totals or {}).get('tax') or 0) > 0, invoice.totals

    post_staged_gl_entries(invoice)

    tax = GlJournal.objects.get(source_id=invoice.pk, source_model='invoice', account=own_account)
    assert tax.credit == float(invoice.totals['tax'])
    assert not GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice',
                                        account=role_account('sales_tax_payable')).exists()
