"""Production is not receiving (Bill, 2026-09-20).

A receipt says goods came from outside: it carries a vendor, terms and an AP ledger. A
workorder owes nobody, so its output is a WorkOrderCompletion on the workorder itself,
and can never become a payable.
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
    from apps.transactions.models import Receipt, WorkOrderCompletion
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)
    assert float((item.quantity or {}).get('on_wo')) == 10.0     # the line committed it

    out = complete_workorder(wo, 'run-1', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('3'), warehouse_code=warehouse.code)])

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
    completion = WorkOrderCompletion.objects.get(pk=out['completions_created'][0])
    assert completion.parent_line_id == line.pk
    assert completion.warehouse_id == warehouse.pk
    assert completion.inventory_layer_id is not None


def test_partial_completions_each_keep_their_own_lot_and_the_line_tracks_the_rest():
    from apps.transactions.models import WorkOrderCompletion
    from apps.transactions.services.transaction_flow import (
        CompleteWorkOrderLine, complete_workorder)
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)

    complete_workorder(wo, 'run-1', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('4'), warehouse_code=warehouse.code, lot='A')])
    complete_workorder(wo, 'run-2', [CompleteWorkOrderLine(
        wo_line_id=line.pk, qty_completed=Decimal('6'), warehouse_code=warehouse.code, lot='B')])

    line.refresh_from_db()
    item.refresh_from_db()
    lots = sorted(c.lot for c in WorkOrderCompletion.objects.filter(parent_line_id=line.pk))
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
