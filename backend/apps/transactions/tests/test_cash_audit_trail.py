"""A cash application balances exactly and says so in words (Bill, 2026-09-25).

"Size does not matter. Exact balancing does matter." One Pending moves the cash and the
document by the same amount; its comments.process names both, and so do the Cash's and the
document's. Any attempt to apply is bounded by the cash's available, never its amount.
"""
from decimal import Decimal

import pytest
from django.db.models import F

from apps.core.models.pending import Pending
from apps.core.services.balance_checker import check_cash_available, check_pendings
from apps.core.services.comment_stamp import append_comment
from apps.transactions.models import Cash, Invoice, Receipt
from apps.transactions.services.cash import cash_door
from apps.transactions.services.cash.cash_pending import (
    CASH_PURPOSE, apply_cash_to_invoice, note_application, unapply_cash_application)
from apps.transactions.services.cash.cash_pending_receipt import apply_cash_to_receipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def buyer(db):
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company='Audit Trail Customer', org_type='customer',
                                  is_active=True)


@pytest.fixture
def seller(db):
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company='Audit Trail Vendor', org_type='vendor',
                                  is_active=True)


def _invoice(customer_id, total='50.00'):
    return Invoice.objects.create(
        customer_id=customer_id, status='open',
        totals={'total': float(Decimal(total)), 'received': 0.0,
                'balance': float(Decimal(total))})


def _cash(amount='10.00', customer_id=None, vendor_id=None):
    return Cash.objects.create(
        amount=Decimal(amount), available=Decimal(amount), status='completed',
        method='check', customer_id=customer_id, vendor_id=vendor_id)


def _lines(record):
    record.refresh_from_db()
    return [e['mgs'] for e in (record.comments or {}).get('process') or []]


# ── exact balance, any size ──────────────────────────────────────────

def test_bills_example_2_11_from_10_00_against_a_50_00_invoice(buyer):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    result = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('2.11'))

    cash.refresh_from_db(); invoice.refresh_from_db()
    assert cash.available == Decimal('7.89')
    assert Decimal(str(invoice.totals['balance'])) == Decimal('47.89')
    assert Decimal(str(invoice.totals['received'])) == Decimal('2.11')

    pending = Pending.objects.get(pk=result['pending_id'])
    [line] = _lines(pending)
    assert f"cash {cash.pk}" in line and f"invoice {invoice.pk}" in line and '2.11' in line
    assert _lines(cash) == [f"2.11 applied to invoice {invoice.pk}" +
                            (f" ({invoice.ida})" if invoice.ida else "") + f", Pending {pending.pk}"]
    [inv_line] = _lines(invoice)
    assert f"received from cash {cash.pk}" in inv_line and f"Pending {pending.pk}" in inv_line


def test_each_entry_carries_the_standard_stamp(buyer):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    pending = Pending.objects.get(pk=apply_cash_to_invoice(cash.pk, invoice.pk,
                                                           Decimal('1.00'))['pending_id'])
    [entry] = pending.comments['process']
    assert {'user', 'mgs', 'time', 'user_id'} <= set(entry)
    assert entry['source'] == 'cash_door'


def test_a_reversal_is_written_on_all_three_records(buyer):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    first = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('3.00'))['pending_id']
    unapply_cash_application(first, reason='wrong invoice')

    reversal = Pending.objects.get(purpose=CASH_PURPOSE, changes__reverses=first)
    assert _lines(reversal)[0].startswith('reversed -3.00')
    assert f"reverses #{first}" in _lines(reversal)[0]
    assert any('reversed to invoice' in l and 'wrong invoice' in l for l in _lines(cash))
    assert any('reversed from cash' in l for l in _lines(invoice))
    cash.refresh_from_db()
    assert cash.available == Decimal('10.00')


def test_a_retry_writes_nothing_twice(buyer):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    pending = Pending.objects.get(pk=apply_cash_to_invoice(cash.pk, invoice.pk,
                                                           Decimal('2.00'))['pending_id'])
    note_application(pending, 'applied')
    note_application(pending, 'applied')
    assert len(_lines(pending)) == 1
    assert len(_lines(cash)) == 1
    assert len(_lines(invoice)) == 1


def test_append_comment_with_a_key_is_idempotent():
    class R:
        comments = {}
    r = R()
    assert append_comment(r, 'process', 'one', key='k') is True
    assert append_comment(r, 'process', 'one again', key='k') is False
    assert [e['mgs'] for e in r.comments['process']] == ['one']


def test_a_queued_application_names_cash_and_invoice(buyer, monkeypatch):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    monkeypatch.setattr(Pending, '_apply_cash', lambda self: False)      # locked: queued
    pending = Pending.objects.create(
        model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
        changes={'cash_id': cash.pk, 'invoice_id': invoice.pk, 'amount': 4.0,
                 'state': 'pending', 'dt_applied': None})
    [line] = _lines(pending)
    assert line.startswith('queued 4.00') and f"cash {cash.pk}" in line and f"invoice {invoice.pk}" in line
    assert _lines(cash) == [] and _lines(invoice) == [], "no money moved: nothing on either side"

    cash_door.close_queued(pending, 'entered twice')
    assert _lines(pending)[-1].startswith('closed 4.00') and 'entered twice' in _lines(pending)[-1]


def test_ap_application_is_written_on_the_receipt(seller):
    receipt = Receipt.objects.create(vendor_id=seller.pk, status='open',
                                     totals={'total': 80.0, 'paid': 0.0, 'balance': 80.0})
    cash = _cash(amount='-80.00', vendor_id=seller.pk)
    result = apply_cash_to_receipt(cash.pk, receipt.pk, Decimal('30.00'))
    pending = Pending.objects.get(pk=result['pending_id'])
    assert f"receipt {receipt.pk}" in _lines(pending)[0]
    assert any(f"received from cash {cash.pk}" in l for l in _lines(receipt))
    assert any(f"applied to receipt {receipt.pk}" in l for l in _lines(cash))


# ── the bound is available, not amount ───────────────────────────────

def test_an_application_is_bounded_by_available(buyer):
    cash = _cash(customer_id=buyer.pk)
    apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('9.00'))
    with pytest.raises(ValueError, match='1.00 available'):
        apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('2.00'))
    apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('1.00'))
    cash.refresh_from_db()
    assert cash.available == Decimal('0.00')


def test_queued_applications_are_set_aside_before_the_bound(buyer, monkeypatch):
    cash = _cash(customer_id=buyer.pk)
    monkeypatch.setattr(Pending, '_apply_cash', lambda self: False)
    Pending.objects.create(model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
                           changes={'cash_id': cash.pk, 'invoice_id': _invoice(buyer.pk).pk,
                                    'amount': 8.0, 'state': 'pending', 'dt_applied': None})
    with pytest.raises(ValueError, match='2.00 available'):
        apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('5.00'))


def test_a_drifted_available_is_corrected_before_it_bounds(buyer, caplog):
    cash = _cash(customer_id=buyer.pk)
    Cash.objects.filter(pk=cash.pk).update(available=Decimal('0.00'))   # wc_demo cash 58-60
    apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('2.11'))
    cash.refresh_from_db()
    assert cash.available == Decimal('7.89')
    assert any('the Pendings say' in r.getMessage() for r in caplog.records)


# ── the balance checker sees it ──────────────────────────────────────

def test_checker_flags_a_drifted_available_even_without_a_customer():
    cash = _cash()                                    # no customer, like wc_demo 58-60
    Cash.objects.filter(pk=cash.pk).update(available=Decimal('0.00'))
    [finding] = [f for f in check_cash_available() if f['record_id'] == cash.pk]
    assert finding['check'] == 'cash.available'
    assert finding['have'] == 0.0 and finding['expect'] == 10.0


def test_checker_passes_a_cash_in_step(buyer):
    cash = _cash(customer_id=buyer.pk)
    apply_cash_to_invoice(cash.pk, _invoice(buyer.pk).pk, Decimal('2.11'))
    assert not [f for f in check_cash_available() if f['record_id'] == cash.pk]


def test_checker_flags_a_pending_processed_but_never_applied(buyer, monkeypatch):
    cash, invoice = _cash(customer_id=buyer.pk), _invoice(buyer.pk)
    monkeypatch.setattr(Pending, '_apply_cash', lambda self: False)
    p = Pending.objects.create(model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
                               changes={'cash_id': cash.pk, 'invoice_id': invoice.pk,
                                        'amount': 100.0, 'state': 'pending'})
    Pending.objects.filter(pk=p.pk).update(dt_processed=F('dt_created'))   # wc_demo #850
    findings, _ = check_pendings()
    assert [f for f in findings if f['check'] == 'pending.limbo' and f['record_id'] == p.pk]


def test_an_overspend_written_around_the_check_is_flagged(buyer):
    """The creation check refuses it; a path that writes a Pending directly does not ask.
    The applier still applies (Rule 10) — the checker says so at once."""
    cash, invoice = _cash(customer_id=buyer.pk), _invoice(buyer.pk)
    for _ in range(2):                                   # two 1,500s against 10.00, uncheck'd
        Pending.objects.create(model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
                               changes={'cash_id': cash.pk, 'invoice_id': invoice.pk,
                                        'amount': 6.0, 'state': 'pending', 'dt_applied': None})
    findings = [f for f in check_cash_available(cash_id=cash.pk)]
    assert [f['check'] for f in findings] == ['cash.overspent']
    assert findings[0]['have'] == -2.0


def test_an_unapply_raises_no_false_drift_warning(buyer, caplog):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    first = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('3.00'))['pending_id']
    caplog.clear()
    unapply_cash_application(first, reason='test')
    assert not [r for r in caplog.records if 'found at' in r.getMessage()]


def test_the_audit_line_names_the_person_who_applied(buyer):
    from django.contrib.auth import get_user_model
    person = get_user_model().objects.create(email='pat.audit@example.com',
                                             name_first='Pat', name_last='Audit')
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    pending = Pending.objects.get(pk=apply_cash_to_invoice(
        cash.pk, invoice.pk, Decimal('1.00'), acted_by=person.pk)['pending_id'])
    [entry] = pending.comments['process']
    assert entry['user'] == 'Pat Audit' and entry['user_id'] == person.pk
    cash.refresh_from_db()
    assert cash.comments['process'][0]['user_id'] == person.pk
