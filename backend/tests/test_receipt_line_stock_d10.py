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
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    Warehouse.objects.create(code='WH1', name='Main')   # the default warehouse stock lands in
    po = Purchase.objects.create(ida='PO-D10')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    out = run_command(Actor.system(), 'convert', 'purchase', po.pk,
                      {'to': 'receipt', 'lines': [{'line_id': pol.pk, 'qty': qty}]})
    from apps.transactions.models import ReceiptLine
    line = ReceiptLine.objects.get(receipt_id=out['receipt_id'])
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
    assert out['layers'] == [line.inventory_layer_id]
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


def test_a_receipt_cut_below_what_it_issued_applies_and_records_the_shortfall():
    """Rule 10 (Bill, 2026-09-21): a Pending applies. Bill, 2026-09-26: a receipt reduced below
    what its layer already issued is allowed and the shortfall is recorded: the layer holds what
    left it, and an open deficit Pending carries the rest, as a short sale's does."""
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    from apps.core.services.balance_checker import check_inventory
    item, line, _ = _received(qty=7, ordered=10)
    layer = line.inventory_layer
    layer.quantity = {**layer.quantity, 'issued': 7}
    layer.save(update_fields=['quantity'])
    _set_qty(line, 6)
    assert _stock(item) == (6, 6, 4)
    assert _layer_received(line) == 7                  # never below what it issued
    deficits = Pending.objects.filter(purpose=DEFICIT_PURPOSE, record_id=str(item.pk), dt_processed=0)
    assert [float(d.changes['deficit_qty']) for d in deficits] == [1.0]
    findings, _ = check_inventory(item_id=item.pk)
    assert not any(f['check'] == 'inventory.layer_range' for f in findings)