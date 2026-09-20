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


# ── a count is a workorder used as an audit tool (Bill, 2026-09-20) ──────


def _item_with_stock(on_hand=10):
    from apps.products.models import Item, Warehouse
    item = Item.objects.create(name='Widget', quantity={'on_hand': on_hand, 'on_wo': 0,
                                                        'allocated': 0, 'available': on_hand})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    return item, warehouse


def test_a_count_moves_stock_to_what_the_counter_saw():
    from apps.transactions.models import Receipt, WorkOrder, WorkOrderCompletion
    from apps.transactions.services.transaction_flow import CountLine, count_inventory
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    item, warehouse = _item_with_stock(on_hand=10)

    out = count_inventory('count-1', [CountLine(
        item_id=item.pk, counted=8, warehouse_code=warehouse.code)],
        counted_by='bill', notes='aisle 3')

    item.refresh_from_db()
    assert float((item.quantity or {}).get('on_hand')) == 8.0     # what the counter saw
    assert out['variance_total'] == -2.0

    wo = WorkOrder.objects.get(pk=out['workorder_id'])
    line = wo.lines.first()
    assert wo.kind == WorkOrder.KIND_COUNT
    assert float((line.quantity or {}).get('staged')) == 10.0     # the book
    assert float((line.quantity or {}).get('active')) == 8.0      # the count
    count = WorkOrderCompletion.objects.get(pk=out['completions_created'][0]).metadata['count']
    assert count['variance'] == -2.0 and count['counted_by'] == 'bill'
    assert count['moved_during_count'] is False

    # a count owes nobody
    assert Receipt.objects.count() == 0
    assert Ledger.objects.filter(model_name='receipt').count() == 0


def test_a_count_line_commits_nothing():
    """Counting reserves no stock: on_wo is untouched while the count is open."""
    from apps.transactions.services.transaction_flow import CountLine, count_inventory
    item, warehouse = _item_with_stock(on_hand=10)

    count_inventory('count-1', [CountLine(item_id=item.pk, counted=10,
                                          warehouse_code=warehouse.code)], counted_by='bill')

    item.refresh_from_db()
    assert float((item.quantity or {}).get('on_wo') or 0) == 0.0


def test_a_count_needs_someone_answerable_for_it():
    from django.core.exceptions import ValidationError
    from apps.transactions.services.transaction_flow import CountLine, count_inventory
    item, warehouse = _item_with_stock()
    with pytest.raises(ValidationError):
        count_inventory('count-1', [CountLine(item_id=item.pk, counted=5,
                                              warehouse_code=warehouse.code)], counted_by='')


def test_found_stock_gets_a_cost_layer_and_missing_stock_does_not():
    from apps.products.models import InventoryLayer
    from apps.transactions.services.transaction_flow import CountLine, count_inventory
    item, warehouse = _item_with_stock(on_hand=10)

    found = count_inventory('count-up', [CountLine(
        item_id=item.pk, counted=12, warehouse_code=warehouse.code,
        reason='found', unit_cost=3.00)], counted_by='bill')
    assert len(found['stacks_created']) == 1
    layer = InventoryLayer.objects.get(pk=found['stacks_created'][0])
    assert float((layer.quantity or {}).get('received')) == 2.0

    short = count_inventory('count-down', [CountLine(
        item_id=item.pk, counted=9, warehouse_code=warehouse.code,
        reason='shrinkage')], counted_by='bill')
    assert short['stacks_created'] == []
    item.refresh_from_db()
    assert float((item.quantity or {}).get('on_hand')) == 9.0


def test_a_count_holds_no_commitment_to_reconcile_or_close():
    from apps.products.management.commands.rebuild_commitment_buckets import commitment_gaps
    from apps.transactions.services.close_transaction import stale_commitments
    from apps.transactions.services.transaction_flow import CountLine, count_inventory
    item, warehouse = _item_with_stock(on_hand=10)

    out = count_inventory('count-1', [CountLine(item_id=item.pk, counted=7,
                                                warehouse_code=warehouse.code)], counted_by='bill')

    assert commitment_gaps(item_id=item.pk) == []        # on_wo owes the count nothing
    assert not [r for r in stale_commitments(days=0)
                if r['model'] == 'workorder' and r['id'] == out['workorder_id']]
