"""A receipt that has received goods reads 'released'; its paid state is its totals (Bill,
2026-11-26: "Released when received", then "Let's land these items" on option (a)).

Saving a receipt receives its goods (readme 108, R1), yet convert left every receipt 'planned' and a
payment rewrote the status to open/partially_paid/paid (cash_door._refresh_receipt_status, now
gone). So a received receipt read 'planned', a paid one lost that it was received, and the first
journalize froze 'planned' for good. Now: status is the document's, paid is a figure, as on an
invoice.
"""
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.services.door import Actor
from apps.core.services.save import save_record
from apps.core.services.verbs import run_command

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


def _received(qty=7, ordered=10):
    """A purchase converted to a receipt: the receipt receives at the save."""
    from apps.accounts.models import Term
    from apps.orgs.models import Vendor
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine, Receipt
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    Warehouse.objects.get_or_create(code='WH1', defaults={'name': 'Main'})
    vendor = Vendor.objects.create(company='Released Vendor')
    po = Purchase.objects.create(ida='PO-REL', vendor_id=vendor.pk, terms='N30')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    out = run_command(Actor.system(), 'convert', 'purchase', po.pk,
                      {'to': 'receipt', 'lines': [{'line_id': pol.pk, 'qty': qty}]})
    _received.answer = out                      # what convert said
    return Receipt.objects.get(pk=out['receipt_id']), vendor


def _cash_out(vendor, amount):
    from apps.transactions.models import Cash
    return Cash.objects.create(amount=Decimal(f'-{amount}'), available=Decimal(f'-{amount}'),
                               status='complete', method='check', vendor_id=vendor.pk)


# ── released when received ────────────────────────────────────────────────

def test_a_converted_receipt_is_released_by_its_receiving_and_says_nothing_of_it():
    """No prompt, no message about the status (Bill, 2026-11-26); Alice watches and coaches."""
    receipt, _ = _received()
    assert receipt.status == 'released'
    assert not any('status' in m for m in _received.answer['messages'])


def test_a_receipt_that_has_received_nothing_stays_planned():
    from apps.orgs.models import Vendor
    from apps.transactions.models import Receipt, ReceiptLine
    receipt = Receipt.objects.create(status='planned', vendor_id=Vendor.objects.create(company='V').pk)
    ReceiptLine.objects.create(receipt=receipt, item={'description': 'On the way'},
                               quantity={'active': 0, 'staged': 5}, cost={'unit': 1.0})
    save_record(Actor.system(), {'id': receipt.pk, 'version': receipt.version, 'terms': 'N30'},
                model_key='receipt')
    receipt.refresh_from_db()
    assert receipt.status == 'planned'


def test_a_status_the_person_set_stays_when_the_receipt_is_saved_again():
    receipt, _ = _received()
    save_record(Actor.system(), {'id': receipt.pk, 'version': receipt.version, 'status': 'approved'},
                model_key='receipt')
    receipt.refresh_from_db()
    save_record(Actor.system(), {'id': receipt.pk, 'version': receipt.version, 'terms': 'DOR'},
                model_key='receipt')
    receipt.refresh_from_db()
    assert receipt.status == 'approved'


# ── paid is a figure ──────────────────────────────────────────────────────

def test_paying_a_receipt_moves_its_figures_never_its_status():
    from apps.transactions.services.cash.cash_pending import unapply_cash_application
    from apps.transactions.services.cash.cash_pending_receipt import apply_cash_to_receipt
    receipt, vendor = _received(qty=10)
    total = Decimal(str(receipt.totals['total']))
    assert total > 0

    part = apply_cash_to_receipt(_cash_out(vendor, total).pk, receipt.pk, total / 2)
    receipt.refresh_from_db()
    assert (receipt.status, receipt.totals['cash_state']) == ('released', 'partial')

    rest = apply_cash_to_receipt(_cash_out(vendor, total).pk, receipt.pk, total / 2)
    receipt.refresh_from_db()
    assert (receipt.status, receipt.totals['cash_state']) == ('released', 'paid')

    unapply_cash_application(rest['pending_id'], reason='wrong bill')
    unapply_cash_application(part['pending_id'], reason='wrong bill')
    receipt.refresh_from_db()
    assert (receipt.status, receipt.totals['cash_state']) == ('released', 'open')


# ── journalize releases a planned receipt in the same act ────────────────

@pytest.mark.usefixtures('chart_of_accounts')
def test_journalizing_a_planned_receipt_releases_it_in_the_same_act():
    from apps.transactions.models import Receipt
    receipt, _ = _received()
    Receipt.objects.filter(pk=receipt.pk).update(status='planned', terms='N30')   # an older receipt
    result = run_command(Actor.system(), 'journalize', 'receipt', receipt.pk, {})
    receipt.refresh_from_db()
    assert receipt.status == 'released' and receipt.dt_journaled
    assert 'released and posted' in str(result)


@pytest.mark.usefixtures('chart_of_accounts')
def test_a_receipt_on_hold_still_posts_and_stays_on_hold():
    from apps.transactions.models import Receipt
    receipt, _ = _received()
    Receipt.objects.filter(pk=receipt.pk).update(status='on_hold', terms='N30')
    run_command(Actor.system(), 'journalize', 'receipt', receipt.pk, {})
    receipt.refresh_from_db()
    assert receipt.status == 'on_hold' and receipt.dt_journaled


# ── the one-off move of older receipts, through the door ─────────────────

def test_the_older_receipts_move_through_the_door_only_when_applied():
    from apps.transactions.models import Receipt
    receipt, _ = _received()
    Receipt.objects.filter(pk=receipt.pk).update(status='planned')
    out = StringIO()
    call_command('release_received_receipts', stdout=out)
    assert "'planned' -> 'released'" in out.getvalue() and '1 to release' in out.getvalue()
    assert Receipt.objects.get(pk=receipt.pk).status == 'planned'

    call_command('release_received_receipts', '--apply', stdout=StringIO())
    moved = Receipt.objects.get(pk=receipt.pk)
    assert moved.status == 'released' and moved.version > receipt.version
