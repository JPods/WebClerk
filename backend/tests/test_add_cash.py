"""POST /wcapi/<invoice|receipt|order>/<id>/add_cash/ — release #9 (Bill, 2026-09-26).

One service: save_record the Cash, then apply it, in one transaction. amount is what the
document is paid (+) or credited (−); the Cash carries its side's checkbook sign.
"""
from decimal import Decimal

import pytest

from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine, Order, Receipt, ReceiptLine
from apps.transactions.services.pricing.totals_compute import recalculate_totals

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model):
    admin = django_user_model.objects.create_user(email='addcash@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    return client


def _post(client, model, pk, body):
    return client.post(f'/wcapi/{model}/{pk}/add_cash/', body, content_type='application/json')


def _data(r):
    d = r.json()['data']
    return d.get('result', d)


def _invoice(unit=100.0):
    buyer = OrgBase.objects.create(company='Add Cash Buyer', org_type='customer', is_active=True)
    inv = Invoice.objects.create(customer_id=buyer.pk, finance={"sales_tax_rate": 0})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": unit, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    return inv


def test_cash_added_to_an_invoice_is_applied_at_once(admin_client):
    inv = _invoice(100.0)
    r = _post(admin_client, 'invoice', inv.pk,
              {'amount': '40.00', 'method': 'check', 'reference': '1042', 'reason': 'mailed check'})
    assert r.status_code == 200, r.content
    cash = Cash.objects.get(pk=_data(r)['cash_id'])
    assert (cash.amount, cash.method, cash.reference_number, cash.invoice_id,
            cash.customer_id) == (Decimal('40.00'), 'check', '1042', inv.pk, inv.customer_id)
    assert cash.available == Decimal('0.00')
    assert cash.comments['process'][0]['mgs'] == 'mailed check'
    inv.refresh_from_db()
    assert (inv.totals['received'], inv.totals['balance']) == (40.0, 60.0)


def test_cash_added_to_a_receipt_pays_the_vendor_with_the_ap_sign(admin_client):
    vendor = OrgBase.objects.create(company='Add Cash Vendor', org_type='vendor', is_active=True)
    receipt = Receipt.objects.create(vendor_id=vendor.pk)
    ReceiptLine.objects.create(receipt=receipt, quantity={'active': 1}, cost={'unit': 100.0, 'precision': 2})
    receipt.refresh_from_db()
    r = _post(admin_client, 'receipt', receipt.pk, {'amount': '60.00', 'method': 'ach'})
    assert r.status_code == 200, r.content
    cash = Cash.objects.get(pk=_data(r)['cash_id'])
    assert cash.amount == Decimal('-60.00') and cash.vendor_id == vendor.pk and cash.receipt_id == receipt.pk
    receipt.refresh_from_db()
    assert (float(receipt.totals['paid']), float(receipt.totals['balance'])) == (60.0, 40.0)


def test_cash_added_to_an_order_is_a_deposit_that_follows_the_order(admin_client):
    from apps.transactions.services.cash.cash_door import relink_deposits
    buyer = OrgBase.objects.create(company='Deposit Buyer', org_type='customer', is_active=True)
    order = Order.objects.create(customer_id=buyer.pk)
    r = _post(admin_client, 'order', order.pk, {'amount': '25.00', 'method': 'cash'})
    assert r.status_code == 200, r.content
    assert _data(r)['deposit'] is True
    cash = Cash.objects.get(pk=_data(r)['cash_id'])
    assert (cash.parent_model, cash.parent_id, cash.invoice_id) == ('order', order.pk, None)
    assert cash.available == Decimal('25.00'), 'unapplied: it waits for the invoice'
    assert not Pending.objects.filter(purpose='cash_application', changes__cash_id=cash.pk).exists()
    inv = Invoice.objects.create(customer_id=buyer.pk)
    assert relink_deposits(order, inv) == 1


def test_a_refused_apply_keeps_the_cash_and_says_why(admin_client, monkeypatch):
    """Bill, 2026-09-26: the apply is completely after the save; a refused apply leaves the
    Cash saved and available, and the answer says why."""
    from apps.transactions.services.cash import cash_pending
    inv = _invoice(100.0)
    monkeypatch.setattr(cash_pending, 'apply_cash_to_invoice',
                        lambda *a, **k: (_ for _ in ()).throw(ValueError('refused for the test')))
    r = _post(admin_client, 'invoice', inv.pk, {'amount': '10.00'})
    assert r.status_code == 200, r.content
    body = _data(r)
    assert body['applied']['state'] == 'refused' and 'refused for the test' in body['applied']['reason']
    cash = Cash.objects.get(pk=body['cash_id'])
    assert cash.available == Decimal('10.00'), 'saved and available to apply'
    inv.refresh_from_db()
    assert inv.totals['received'] == 0.0


@pytest.mark.parametrize('body, code', [
    ({'amount': '0'}, 'amount_required'),
    ({'amount': '500.00'}, 'amount_exceeds_balance'),
])
def test_bad_amounts_are_coached(admin_client, body, code):
    inv = _invoice(100.0)
    r = _post(admin_client, 'invoice', inv.pk, body)
    assert r.status_code == 400 and r.json()['error']['code'] == code, r.content
