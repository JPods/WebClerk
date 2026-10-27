"""The journal entry a document makes, before and after it posts (Bill, 2026-10-27).

The flight simulator previews an invoice's, a cash's and a receipt's journal entry, then
posts it. The preview runs the real journalize and rolls back: it writes nothing, and what
it shows is exactly what the journalize command then writes.
"""
import pytest

from apps.accounts.models import GlJournal
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine
from apps.transactions.services.pricing.totals_compute import recalculate_totals

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model, chart_of_accounts):
    admin = django_user_model.objects.create_user(email='journal@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    return client


def _invoice(unit=100.0):
    buyer = OrgBase.objects.create(company='Journal Buyer', org_type='customer', is_active=True)
    inv = Invoice.objects.create(customer_id=buyer.pk, finance={'sales_tax_rate': 0})
    InvoiceLine.objects.create(invoice=inv, quantity={'active': 1},
                               price={'unit': unit, 'precision': 2}, cost={'unit': 0})
    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    return inv


def _command(client, model, pk, verb, body=None):
    return client.post(f'/wcapi/{model}/{pk}/{verb}/', body or {}, content_type='application/json')


def _result(r):
    assert r.status_code == 200, r.content
    return r.json()['data']['result']


def _lines(entries):
    return sorted((e['account'], e['debit'], e['credit']) for e in entries)


def test_the_preview_writes_nothing_and_is_what_posting_writes(admin_client):
    inv = _invoice(100.0)
    before = GlJournal.objects.count()

    preview = _result(_command(admin_client, 'invoice', inv.pk, 'journal_preview'))
    assert preview['posted'] is False and preview['balanced'] and preview['entries']
    assert GlJournal.objects.count() == before
    inv.refresh_from_db()
    assert not inv.dt_journaled

    _result(_command(admin_client, 'invoice', inv.pk, 'journalize'))
    written = GlJournal.objects.filter(source_model='invoice', source_id=inv.pk)
    assert _lines([{'account': g.account, 'debit': float(g.debit or 0), 'credit': float(g.credit or 0)}
                   for g in written]) == _lines(preview['entries'])

    after = _result(_command(admin_client, 'invoice', inv.pk, 'journal_preview'))
    assert after['posted'] is True and _lines(after['entries']) == _lines(preview['entries'])


def test_posting_twice_is_refused(admin_client):
    inv = _invoice(50.0)
    _result(_command(admin_client, 'invoice', inv.pk, 'journalize'))
    r = _command(admin_client, 'invoice', inv.pk, 'journalize')
    assert r.status_code == 409 and r.json()['error']['code'] == 'already_journalized', r.content


def test_a_write_off_previews_to_its_loss_account(admin_client):
    inv = _invoice(10.0)
    r = admin_client.post(f'/wcapi/invoice/{inv.pk}/add_cash/',
                          {'amount': '9.83', 'method': 'check', 'write_off_rest': True},
                          content_type='application/json')
    off = Cash.objects.get(pk=_result(r)['written_off']['cash_id'])
    _result(_command(admin_client, 'invoice', inv.pk, 'journalize'))
    preview = _result(_command(admin_client, 'cash', off.pk, 'journal_preview'))
    assert preview['balanced'] and not preview['posted']
    debit = [e for e in preview['entries'] if e['debit']]
    assert debit and debit[0]['debit'] == 0.17 and 'receivable' not in debit[0]['account']
    assert any(e['credit'] == 0.17 and 'receivable' in e['account'] for e in preview['entries'])
