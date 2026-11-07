"""A GL row is posted the moment it is written (the lead, 2026-11-07): GlJournal.save stamps
dt_journaled, so the dashboard's unposted count (dashboard_pending) does not grow with postings.
wc_demo held 349 rows at 0 — every posting ever made counted as unposted."""
import pytest

pytestmark = pytest.mark.django_db


def test_a_posting_stamps_its_rows_and_the_dashboard_does_not_count_them_unposted(chart_of_accounts):
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize import journalize_invoice
    from apps.core.services.dashboard.dashboard_pending import get_pending_summary
    from apps.orgs.models import Customer
    from apps.transactions.models import Invoice, InvoiceLine
    buyer = Customer.objects.create(company='Stamp Buyer')
    inv = Invoice.objects.create(customer_id=buyer.pk, terms='N30', status='released', finance={'sales_tax_rate': 0})
    InvoiceLine.objects.create(invoice=inv, quantity={'active': 1}, price={'unit': 50, 'precision': 2}, cost={'unit': 0})
    unposted_before = GlJournal.objects.filter(dt_journaled=0).count()

    assert journalize_invoice(inv.pk)['created'] == 2

    rows = GlJournal.objects.filter(source_id=inv.pk, source_model='invoice')
    assert rows.count() == 2 and all(r.dt_journaled > 0 for r in rows)
    assert GlJournal.objects.filter(dt_journaled=0).count() == unposted_before
    assert get_pending_summary()['metrics'][0]['value'] == f'{unposted_before:,}'

    # A row born with a posting date (a seed's) keeps it.
    born = GlJournal.objects.create(ida='SJ-born', account=rows.first().account, debit=1.0,
                                    source='automation', type='sales', dt_journaled=1700000000000)
    assert born.dt_journaled == 1700000000000
