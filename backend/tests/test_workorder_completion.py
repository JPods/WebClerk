"""Production is not receiving, and what happens to a line lives on the line.

A receipt says goods came from outside: it carries a vendor, terms and an AP ledger. A
workorder owes nobody, so its output is an event in ``workorder_line.events[]``, appended
by the pending applier in the same apply that moves the buckets (Bill, 2026-09-20).
"""
from decimal import Decimal

import pytest
from django.apps import apps as dj_apps

pytestmark = pytest.mark.django_db


def _workorder_with_a_line(qty=10):
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import WorkOrder, WorkOrderLine
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_wo': 0,
                                                        'allocated': 0, 'available': 0})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    wo = WorkOrder.objects.create()
    line = WorkOrderLine.objects.create(
        workorder=wo,
        item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': qty}, cost={'unit': 4.00, 'precision': 2})
    item.refresh_from_db()
    return wo, line, item, warehouse


def test_completing_a_workorder_makes_stock_and_no_payable():
    from apps.transactions.models import Receipt
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)
    assert float((item.quantity or {}).get('on_wo')) == 10.0     # the line committed it

    out = complete_workorder(wo, 'run-1', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('3'), warehouse_code=warehouse.code)],
        completed_by='shift a')

    item.refresh_from_db()
    line.refresh_from_db()
    quantity = item.quantity or {}
    assert float(quantity.get('on_wo')) == 7.0        # no longer work in progress
    assert float(quantity.get('on_hand')) == 3.0      # produced
    assert float(quantity.get('on_rc') or 0) == 0.0   # nothing arrived from outside
    assert float((line.quantity or {}).get('remaining')) == 7.0   # the document moved too

    # and nothing that could become money owed
    assert Receipt.objects.count() == 0
    assert Ledger.objects.filter(model_name='receipt').count() == 0
    event = line.events[0]
    assert event['id'] == out['events_created'][0]
    assert event['kind'] == 'completion' and event['qty'] == 3.0
    assert event['by'] == 'shift a'
    assert event['warehouse_id'] == warehouse.pk
    assert event['layer_id'] is not None


def test_partial_completions_each_keep_their_own_lot_and_the_line_tracks_the_rest():
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)

    complete_workorder(wo, 'run-1', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('4'), warehouse_code=warehouse.code, lot='A')])
    complete_workorder(wo, 'run-2', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('6'), warehouse_code=warehouse.code, lot='B')])

    line.refresh_from_db()
    item.refresh_from_db()
    lots = sorted(e['lot'] for e in line.events)
    assert lots == ['A', 'B']                                   # two runs, two lots
    assert float((line.quantity or {}).get('remaining')) == 0.0  # all of it produced
    assert float((item.quantity or {}).get('on_wo')) == 0.0
    assert float((item.quantity or {}).get('on_hand')) == 10.0


def test_a_receipt_without_a_vendor_owes_nobody():
    """The safety net behind the structure: an internal movement writes no AP row."""
    from apps.transactions.models import Receipt, ReceiptLine
    from apps.accounts.services.terms_ledger import apply_terms_for_payable
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    receipt = Receipt.objects.create(source_type=Receipt.SOURCE_ADJUSTMENT)
    ReceiptLine.objects.create(receipt=receipt, quantity={'active': 2},
                               cost={'unit': 5.00, 'precision': 2})

    rows = apply_terms_for_payable(receipt, replace=True)

    assert rows == []
    assert not Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').exists()


def test_a_receipt_can_no_longer_claim_to_be_a_workorder():
    from apps.transactions.models import Receipt
    assert not hasattr(Receipt, 'SOURCE_WORKORDER')
    assert [code for code, _label in Receipt.SOURCE_CHOICES] == [
        Receipt.SOURCE_PURCHASE, Receipt.SOURCE_ADJUSTMENT]


# ── a count is a workorder used as an audit tool (Bill, 2026-09-20) ──────


def _item_with_stock(on_hand=10):
    from apps.products.models import Item, Warehouse
    item = Item.objects.create(name='Widget', quantity={'on_hand': on_hand, 'on_wo': 0,
                                                        'allocated': 0, 'available': on_hand})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    return item, warehouse


def test_an_event_is_recorded_once_however_often_the_pending_applies():
    """The event id makes an apply idempotent — the guard behind posting through pendings."""
    from apps.core.models import Pending
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)

    complete_workorder(wo, 'run-1', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('3'), warehouse_code=warehouse.code)])

    line.refresh_from_db()
    assert len(line.events) == 1
    pending = Pending.objects.filter(purpose='line_event').latest('id')
    pending.dt_processed = 0                 # make it apply again
    pending.try_apply()

    line.refresh_from_db()
    assert len(line.events) == 1             # recorded once


def test_two_completions_at_once_both_land():
    """Bill's case: 3 and 7 at the same instant, two pendings, both applied."""
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)

    complete_workorder(wo, 'run-a', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('3'), warehouse_code=warehouse.code)],
        completed_by='ann')
    complete_workorder(wo, 'run-b', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('7'), warehouse_code=warehouse.code)],
        completed_by='bob')

    line.refresh_from_db()
    item.refresh_from_db()
    assert sorted(e['qty'] for e in line.events) == [3.0, 7.0]
    assert sorted(e['by'] for e in line.events) == ['ann', 'bob']
    assert float((line.quantity or {}).get('remaining')) == 0.0
    assert float((item.quantity or {}).get('on_hand')) == 10.0
    assert float((item.quantity or {}).get('on_wo')) == 0.0
