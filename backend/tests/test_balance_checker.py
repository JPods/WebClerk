"""balance_checker — does inventory and cash balance, and which event broke it?

Bill, 2026-09-21: *"A dedicated function for Alice of balance_checker"*, *"pending records
should be powerful for this"*, and *"a running log of every cash and inventory event and
if it is properly balanced."*

The checks are invariants and independent axes, never the writer's formula run twice: a
bucket against Σ its applied Pendings, on_hand against Σ its layers.
"""
import json

import pytest

pytestmark = pytest.mark.django_db


def _received(qty=7, ordered=10):
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine
    from apps.transactions.services.transaction_flow import ReceiveLine, receive_purchase
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    po = Purchase.objects.create(ida='PO-BAL')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    receive_purchase(po, 'RC-BAL', [ReceiveLine(po_line_id=pol.pk, qty=qty,
                                                warehouse_code=warehouse.code)])
    return item


def _checks(result):
    return {f['check'] for f in result['findings']}


def test_stock_received_through_the_path_balances():
    from apps.core.services.balance_checker import check_balances
    item = _received()
    result = check_balances(scope=('inventory', 'pending'), item_id=item.pk)
    assert result['balanced'], result['findings']


def test_on_hand_written_without_a_pending_is_caught_on_two_axes():
    from apps.core.services.balance_checker import check_balances
    from apps.products.models import Item
    item = _received(qty=7)
    Item.objects.filter(pk=item.pk).update(
        quantity={**item.__class__.objects.get(pk=item.pk).quantity, 'on_hand': 100, 'available': 100})
    result = check_balances(scope=('inventory',), item_id=item.pk)
    assert not result['balanced']
    assert {'inventory.pending_journal', 'inventory.layers'} <= _checks(result)
    journal = next(f for f in result['findings'] if f['check'] == 'inventory.pending_journal')
    assert (journal['field'], journal['have'], journal['expect']) == ('on_hand', 100.0, 7.0)


def test_available_must_be_on_hand_less_allocated():
    from apps.core.services.balance_checker import check_balances
    from apps.products.models import Item
    item = _received(qty=7)
    q = Item.objects.get(pk=item.pk).quantity
    Item.objects.filter(pk=item.pk).update(quantity={**q, 'available': 3})
    assert 'inventory.available' in _checks(check_balances(scope=('inventory',), item_id=item.pk))


def test_a_layer_that_issued_more_than_it_received_is_out_of_range():
    from apps.core.services.balance_checker import check_balances
    from apps.products.models.inventory_layer import InventoryLayer
    item = _received(qty=7)
    layer = InventoryLayer.objects.get(item_id=item.pk)
    InventoryLayer.objects.filter(pk=layer.pk).update(quantity={**layer.quantity, 'issued': 9})
    assert 'inventory.layer_range' in _checks(check_balances(scope=('inventory',), item_id=item.pk))


def test_a_pending_that_never_applied_is_stuck():
    from apps.core.models import Pending
    from apps.core.services.balance_checker import check_balances
    item = _received()
    p = Pending.objects.create(model_name='item', record_id=str(item.pk),
                               purpose='inventory_qty_change', dt_processed=1,
                               changes={'on_so': 1})
    Pending.objects.filter(pk=p.pk).update(dt_processed=0, dt_created=1)
    result = check_balances(scope=('pending',), item_id=item.pk)
    assert [f['record_id'] for f in result['findings'] if f['check'] == 'pending.stuck'] == [p.pk]


def test_every_event_is_logged_with_whether_it_still_balances(settings, tmp_path,
                                                                django_capture_on_commit_callbacks):
    from apps.core.models import Pending
    from apps.products.models import Item
    settings.BALANCE_EVENT_LOG = True
    settings.BALANCE_EVENT_LOG_PATH = tmp_path / 'balance-events.jsonl'
    with django_capture_on_commit_callbacks(execute=True):
        item = _received(qty=7)
    lines = [json.loads(x) for x in settings.BALANCE_EVENT_LOG_PATH.read_text().splitlines()]
    assert lines and all(x['balanced'] for x in lines if x['applied'])
    assert any(x['changes'].get('on_hand') == 7 for x in lines)

    # A write that skips the path: the next event on that item names the break.
    q = Item.objects.get(pk=item.pk).quantity
    Item.objects.filter(pk=item.pk).update(quantity={**q, 'on_hand': 50, 'available': 50})
    with django_capture_on_commit_callbacks(execute=True):
        Pending.objects.create(model_name='item', record_id=str(item.pk),
                               purpose='inventory_qty_change', changes={'on_so': 1})
    last = json.loads(settings.BALANCE_EVENT_LOG_PATH.read_text().splitlines()[-1])
    assert last['applied'] and not last['balanced']
    assert {f['check'] for f in last['findings']} >= {'inventory.pending_journal', 'inventory.layers'}


def test_the_log_is_off_unless_asked(settings, tmp_path, django_capture_on_commit_callbacks):
    settings.BALANCE_EVENT_LOG = False
    settings.BALANCE_EVENT_LOG_PATH = tmp_path / 'balance-events.jsonl'
    with django_capture_on_commit_callbacks(execute=True):
        _received()
    assert not settings.BALANCE_EVENT_LOG_PATH.exists()
