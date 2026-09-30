"""D10, as ruled 2026-09-28/30: receiving moves a receipt line's stock once, and then it is fixed.

Bill, 2026-09-21: "every change in inventory and cash should generate a pending record" and
"Layers must change with items." Bill, 2026-09-28/30: a layer never changes after it is born
(its cost and its received quantity), goods go on the shelf at the receipt's receive command,
and a correction is a count workorder. So receiving writes one Pending that moves on_hand,
on_rc, on_po and creates the layer; after that the received quantity cannot be edited or the line
deleted. This supersedes the 2026-09-21/26 rule that a receipt line edit moved stock and layer.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.core.services.door import Refused

pytestmark = pytest.mark.django_db


def _planned(qty=7, ordered=10):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine, ReceiptLine
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    Warehouse.objects.create(code='WH1', name='Main')   # the default warehouse stock lands in
    po = Purchase.objects.create(ida='PO-D10')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    out = run_command(Actor.system(), 'convert', 'purchase', po.pk,
                      {'to': 'receipt', 'lines': [{'line_id': pol.pk, 'qty': qty}]})
    return item, ReceiptLine.objects.get(receipt_id=out['receipt_id'])


def _received(qty=7, ordered=10):
    from apps.transactions.services.receive_commands import receive_receipt
    item, line = _planned(qty, ordered)
    out = receive_receipt(line.receipt)
    line.refresh_from_db()
    return item, line, out


def _stock(item):
    item.refresh_from_db()
    q = item.quantity
    return q.get('on_hand'), q.get('on_rc'), q.get('on_po')


def test_receiving_moves_stock_and_creates_the_layer_in_one_pending():
    from apps.core.models import Pending
    item, line, out = _received(qty=7, ordered=10)
    assert _stock(item) == (7, 7, 3)
    assert out['received'] == [{'line_id': line.pk, 'qty': 7, 'layer_id': line.inventory_layer_id}]
    assert line.inventory_layer.quantity['received'] == 7
    assert line.inventory_layer.serial_batch == line.serial_batch
    add = Pending.objects.get(record_id=str(item.pk), purpose='inventory_line_add',
                              changes__layer__line_id=line.pk)
    assert add.is_processed() and add.changes['layer']['line_id'] == line.pk


def test_a_received_quantity_cannot_be_edited():
    item, line, _ = _received(qty=7, ordered=10)
    line.quantity = {**line.quantity, 'active': 6, 'staged': 6}
    with pytest.raises(Refused) as refused:
        line.save()
    assert refused.value.code == 'receive_command'
    assert _stock(item) == (7, 7, 3)


def test_a_received_line_and_its_receipt_cannot_be_deleted():
    from apps.transactions.models.hard_delete import JournalizedDeleteRefused
    item, line, _ = _received(qty=7, ordered=10)
    with pytest.raises(JournalizedDeleteRefused, match='count workorder'):
        line.delete()
    with pytest.raises(JournalizedDeleteRefused, match='count workorder'):
        line.receipt.delete()
    assert _stock(item) == (7, 7, 3)


def test_a_planned_line_may_leave_a_partly_received_receipt():
    from apps.transactions.models import ReceiptLine
    item, line, _ = _received(qty=7, ordered=10)
    planned = ReceiptLine.objects.create(receipt=line.receipt, item=line.item,
                                         quantity={'active': 0, 'staged': 3}, cost={'unit': 4.00},
                                         warehouse_id=line.warehouse_id)
    planned.delete()
    assert _stock(item) == (7, 7, 3)
    assert ReceiptLine.objects.filter(pk=line.pk).exists()


def test_a_receipt_line_needs_a_warehouse_to_land_in():
    from apps.transactions.services.receive_commands import receive_receipt
    item, line = _planned()
    type(line).objects.filter(pk=line.pk).update(warehouse=None)
    with pytest.raises(ValidationError):
        receive_receipt(line.receipt)
    assert _stock(item) == (0, 0, 10)
