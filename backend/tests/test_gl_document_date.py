"""A GL row carries its document's dt_created as dt_document, the period it reports in, beside
dt_journaled, the moment it was posted (Bill, 2026-11-27: "dt_created will be best. It is
simple. If they need to adjust it, an admin or superuser can adjust it."). An invoice posted a
month late belongs to its own month in the period check and in the bundle sent to accounting."""
import datetime

import pytest

pytestmark = pytest.mark.django_db


def _ms(year, month, day):
    return int(datetime.datetime(year, month, day, 12, tzinfo=datetime.timezone.utc).timestamp() * 1000)


def _posted_invoice(created_ms):
    from apps.accounts.services.journalize import journalize_invoice
    from apps.orgs.models import Customer
    from apps.transactions.models import Invoice, InvoiceLine
    buyer = Customer.objects.create(company='Period Buyer')
    inv = Invoice.objects.create(customer_id=buyer.pk, terms='N30', status='released',
                                 finance={'sales_tax_rate': 0})
    InvoiceLine.objects.create(invoice=inv, quantity={'active': 1},
                               price={'unit': 50, 'precision': 2}, cost={'unit': 0})
    Invoice.objects.filter(pk=inv.pk).update(dt_created=created_ms)
    assert journalize_invoice(inv.pk)['created'] == 2
    return inv


def test_a_row_reports_in_its_documents_month_whenever_it_was_posted(chart_of_accounts):
    from apps.accounts.models import GlJournal
    from apps.accounts.services.period_close import _verify_gl_balance
    september = _ms(2026, 9, 15)
    inv = _posted_invoice(september)

    rows = list(GlJournal.objects.filter(source_id=inv.pk, source_model='invoice'))
    assert all(r.dt_document == september for r in rows)
    assert all(r.dt_journaled > september for r in rows), 'posted now, not in September'

    assert _verify_gl_balance(2026, 9)['total_debits'] == 50.0
    posted = datetime.datetime.fromtimestamp(rows[0].dt_journaled / 1000, datetime.timezone.utc)
    if (posted.year, posted.month) != (2026, 9):
        assert _verify_gl_balance(posted.year, posted.month)['total_debits'] == 0


def test_a_reversal_belongs_to_its_documents_month_and_a_row_with_no_document_to_its_posting(chart_of_accounts):
    from apps.accounts.models import GlJournal
    september = _ms(2026, 9, 15)
    inv = _posted_invoice(september)
    account = GlJournal.objects.filter(source_id=inv.pk).first().account

    reversal = GlJournal.objects.create(ida='SJ-rev', account=account, credit=1.0, source='automation',
                                        type='sales', source_model='invoice_reversal', source_id=inv.pk)
    assert reversal.dt_document == september

    manual = GlJournal.objects.create(ida='SJ-man', account=account, debit=1.0, source='manual', type='sales')
    assert manual.dt_document == manual.dt_journaled
