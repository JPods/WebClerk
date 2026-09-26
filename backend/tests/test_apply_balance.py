"""POST /wcapi/invoice/<id>/apply_balance/ — a customer's money applied to an invoice by rule.

Bill, 2026-09-26: "nothing special. Any company should be able to quickly do the same with
any customer." Rules: oldest (no payload) and cash ({cash_id, amount}); more will follow.
"""
from decimal import Decimal

import pytest

from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine
from apps.transactions.services.pricing.totals_compute import recalculate_totals

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model):
    admin = django_user_model.objects.create_user(email='apply-admin@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    return client


def _customer(name):
    return OrgBase.objects.create(company=name, org_type='customer', is_active=True)


def _invoice(customer, unit):
    inv = Invoice.objects.create(customer_id=customer.pk, finance={"sales_tax_rate": 0})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": unit, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    return inv


def _post(client, inv, body=None):
    return client.post(f'/wcapi/invoice/{inv.pk}/apply_balance/', body or {},
                       content_type='application/json')


def test_oldest_applies_the_customers_money_oldest_first_and_leaves_the_rest_open(admin_client):
    buyer = _customer('Oldest Buyer')
    first = Cash.objects.create(amount=Decimal('30.00'), customer_id=buyer.pk)
    second = Cash.objects.create(amount=Decimal('50.00'), customer_id=buyer.pk)
    inv = _invoice(buyer, 100.00)

    r = _post(admin_client, inv)
    assert r.status_code == 200, r.content
    body = r.json()['data']['result'] if 'result' in r.json()['data'] else r.json()['data']
    assert body['rule'] == 'oldest'
    assert [a['cash_id'] for a in body['applied']] == [first.pk, second.pk]

    inv.refresh_from_db()
    assert (inv.totals['received'], inv.totals['balance'], inv.totals['cash_state']) == (80.0, 20.0, 'partial')
    first.refresh_from_db(); second.refresh_from_db()
    assert (first.available, second.available) == (Decimal('0.00'), Decimal('0.00'))


def test_oldest_stops_at_the_balance(admin_client):
    buyer = _customer('Rich Buyer')
    cash = Cash.objects.create(amount=Decimal('500.00'), customer_id=buyer.pk)
    inv = _invoice(buyer, 40.00)
    assert _post(admin_client, inv).status_code == 200
    inv.refresh_from_db(); cash.refresh_from_db()
    assert inv.totals['balance'] == 0.0 and cash.available == Decimal('460.00')


def test_cash_applies_the_named_payments_stated_amount(admin_client):
    buyer = _customer('Named Buyer')
    older = Cash.objects.create(amount=Decimal('100.00'), customer_id=buyer.pk)
    named = Cash.objects.create(amount=Decimal('100.00'), customer_id=buyer.pk)
    inv = _invoice(buyer, 60.00)

    r = _post(admin_client, inv, {'cash_id': named.pk, 'amount': '25.00'})
    assert r.status_code == 200, r.content
    inv.refresh_from_db(); older.refresh_from_db(); named.refresh_from_db()
    assert inv.totals['received'] == 25.0 and inv.totals['balance'] == 35.0
    assert named.available == Decimal('75.00') and older.available == Decimal('100.00'), \
        'only the named payment moved'


@pytest.mark.parametrize('body, code', [
    ({'cash_id': None, 'amount': '5'}, None),               # no cash_id → rule oldest by default
    ({'rule': 'cash', 'amount': '5'}, 'cash_id_required'),
    ({'rule': 'cash', 'cash_id': 1, 'amount': '0'}, 'amount_required'),
    ({'rule': 'mystery'}, 'unknown_rule'),
])
def test_bad_payloads_are_coached(admin_client, body, code):
    buyer = _customer('Coached Buyer')
    inv = _invoice(buyer, 10.00)
    r = _post(admin_client, inv, {k: v for k, v in body.items() if v is not None})
    if code is None:
        assert r.status_code == 200
    else:
        assert r.status_code == 400 and r.json()['error']['code'] == code, r.content


def test_more_than_the_balance_is_refused_and_nothing_moves(admin_client):
    buyer = _customer('Over Buyer')
    cash = Cash.objects.create(amount=Decimal('100.00'), customer_id=buyer.pk)
    inv = _invoice(buyer, 20.00)
    r = _post(admin_client, inv, {'cash_id': cash.pk, 'amount': '30.00'})
    assert r.status_code == 400 and r.json()['error']['code'] == 'amount_exceeds_balance'
    assert not Pending.objects.filter(purpose='cash_application', changes__invoice_id=inv.pk).exists()


def test_another_customers_payment_is_refused_with_the_reason(admin_client):
    buyer, other = _customer('Mine'), _customer('Theirs')
    theirs = Cash.objects.create(amount=Decimal('50.00'), customer_id=other.pk)
    inv = _invoice(buyer, 20.00)
    r = _post(admin_client, inv, {'cash_id': theirs.pk, 'amount': '10.00'})
    assert r.status_code == 409 and r.json()['error']['code'] == 'apply_refused'
    assert 'customers differ' in r.json()['message']
    theirs.refresh_from_db()
    assert theirs.available == Decimal('50.00')


def test_oldest_skips_a_refused_payment_and_the_others_stand(admin_client, monkeypatch):
    """Bill: the rest stays open. One refused application must not undo the others (Fable:
    run_command's single transaction rolled every earlier application back)."""
    from apps.transactions.services.cash import cash_pending
    buyer = _customer('Mixed Buyer')
    first = Cash.objects.create(amount=Decimal('10.00'), customer_id=buyer.pk)
    bad = Cash.objects.create(amount=Decimal('10.00'), customer_id=buyer.pk)
    third = Cash.objects.create(amount=Decimal('10.00'), customer_id=buyer.pk)
    inv = _invoice(buyer, 100.00)
    real = cash_pending.apply_cash_to_invoice

    def refuse_bad(cash_id, *args, **kwargs):
        if cash_id == bad.pk:
            raise ValueError('refused for the test')
        return real(cash_id, *args, **kwargs)
    monkeypatch.setattr(cash_pending, 'apply_cash_to_invoice', refuse_bad)

    r = _post(admin_client, inv)
    assert r.status_code == 200, r.content
    data = r.json()['data']
    states = {a['cash_id']: a['state'] for a in (data.get('result') or data)['applied']}
    assert states == {first.pk: 'applied', bad.pk: 'refused', third.pk: 'applied'}
    inv.refresh_from_db()
    assert inv.totals['received'] == 20.0 and inv.totals['balance'] == 80.0
