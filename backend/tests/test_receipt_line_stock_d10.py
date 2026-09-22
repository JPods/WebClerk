"""D10 — a receipt line moves stock on every change, and its layer moves with it.

Bill, 2026-09-21: *"every change in inventory and cash should generate a pending
record"* and *"Layers must change with items."* A receipt line is one of the six line
types (signals._LINE_CONFIG): add, change and delete each write a Pending, and that
Pending moves on_hand, on_rc, on_po and the layer in one apply — both saved, or neither.

Before: receiving 7 then correcting to 6 moved the money and left the stock at 7.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db


def _received(qty=7, ordered=10):
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine
    from apps.transactions.services.transaction_flow import ReceiveLine, receive_purchase
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    po = Purchase.objects.create(ida='PO-D10')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    out = receive_purchase(po, 'RC-D10', [ReceiveLine(po_line_id=pol.pk, qty=qty,
                                                      warehouse_code=warehouse.code)])
    from apps.transactions.models import ReceiptLine
    line = ReceiptLine.objects.get(pk=out['receipt_lines_created'][0])
    return item, line, out


def _stock(item):
    item.refresh_from_db()
    q = item.quantity
    return q.get('on_hand'), q.get('on_rc'), q.get('on_po')


def _layer_received(line):
    line.refresh_from_db()
    line.inventory_layer.refresh_from_db()
    return line.inventory_layer.quantity['received']


def _set_qty(line, qty):
    line.quantity = {**line.quantity, 'active': qty, 'staged': qty}
    line.save()


def test_receiving_moves_stock_and_creates_the_layer_in_one_pending():
    from apps.core.models import Pending
    item, line, out = _received(qty=7, ordered=10)
    assert _stock(item) == (7, 7, 3)
    assert out['stacks_created'] == [line.inventory_layer_id]
    assert _layer_received(line) == 7
    assert line.inventory_layer.serial_batch == line.serial_batch
    add = Pending.objects.get(record_id=str(item.pk), purpose='inventory_line_add',
                              changes__type_id='RC')
    assert add.is_processed() and add.changes['layer']['line_id'] == line.pk
    assert not Pending.objects.filter(purpose='receipt_line_add').exists()


def test_a_receipt_line_edit_moves_stock_and_layer():
    item, line, _ = _received(qty=7, ordered=10)
    _set_qty(line, 6)
    assert _stock(item) == (6, 6, 4)          # was (7, 7, 3): the D10 defect
    assert _layer_received(line) == 6


def test_a_receipt_line_delete_gives_the_goods_back():
    item, line, _ = _received(qty=7, ordered=10)
    layer = line.inventory_layer
    line.delete()
    assert _stock(item) == (0, 0, 10)
    layer.refresh_from_db()
    assert layer.quantity['received'] == 0


def test_a_receipt_line_needs_a_warehouse_to_land_in():
    from apps.transactions.models import ReceiptLine
    item, line, _ = _received()
    with pytest.raises(ValidationError):
        ReceiptLine.objects.create(receipt=line.receipt, item=line.item,
                                   quantity={'active': 1, 'staged': 1}, cost={'unit': 4.00})


def test_a_locked_layer_holds_the_item_back_until_both_can_move():
    from apps.core.models import Pending
    from apps.transactions.services.inventory_pending_process import process_pending_for_item
    item, line, _ = _received(qty=7, ordered=10)
    layer = line.inventory_layer
    layer.acquire_lock()

    _set_qty(line, 6)
    waiting = Pending.objects.get(record_id=str(item.pk), purpose='inventory_qty_change')
    assert not waiting.is_processed()
    assert _stock(item) == (7, 7, 3)          # neither moved
    assert _layer_received(line) == 7

    layer.release_lock()                       # drains the queue through the one applier
    waiting.refresh_from_db()
    assert waiting.is_processed()
    assert _stock(item) == (6, 6, 4)
    assert _layer_received(line) == 6
    assert process_pending_for_item(item.pk)['total_found'] == 0


def test_giving_back_goods_already_issued_applies_and_is_a_finding():
    """Rule 10 (Bill, 2026-09-21): a Pending applies. The applier does not refuse a layer
    that ends up holding less than it issued; check_balances reports it, and the user
    corrects it with a new record."""
    from apps.core.services.balance_checker import check_inventory
    item, line, _ = _received(qty=7, ordered=10)
    layer = line.inventory_layer
    layer.quantity = {**layer.quantity, 'issued': 7}
    layer.save(update_fields=['quantity'])
    _set_qty(line, 6)
    assert _stock(item) == (6, 6, 4)
    assert _layer_received(line) == 6
    findings, _ = check_inventory(item_id=item.pk)
    assert any(f['check'] == 'inventory.layer_range' for f in findings)
