"""D10, as ruled 2026-11-11 (readme 108): a receipt line's quantity moves its stock AND its money.

D10 (2026-09-20): a receipt-line edit moved the money and not the stock. Bill, 2026-11-11: saving a
receipt receives the goods (R1), the dock cost never changes (R3), and a received quantity may be
corrected until the receipt is journalized ("Amendment confirmed"): the line's one layer moves by the
difference, a reduction only while the layer still holds those units, and the receipt's journal posts
the net. Journalized: refused. A received line is not deleted (a count workorder corrects it).
"""
import pytest
from django.core.exceptions import ValidationError

from apps.core.services.door import Refused

pytestmark = pytest.mark.django_db




def _complete_vendor():
    """A purchase names its vendor and terms, or the money steps refuse it (the team, 2026-11-06)."""
    from apps.accounts.models import Term
    from apps.orgs.models import Vendor
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    return Vendor.objects.create(company='Complete Vendor')
def _received(qty=7, ordered=10):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine, ReceiptLine
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    Warehouse.objects.create(code='WH1', name='Main')   # the default warehouse stock lands in
    po = Purchase.objects.create(ida='PO-D10', vendor_id=_complete_vendor().pk, terms='N30')
    pol = PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': ordered, 'staged': ordered}, cost={'unit': 4.00})
    from apps.transactions.services.convert.convert import convert_and_save
    out = convert_and_save(Actor.system(), 'purchase', po.pk, 'receipt', named={pol.pk: qty})
    return item, ReceiptLine.objects.get(receipt_id=out['receipt_id']), out


def _stock(item):
    item.refresh_from_db()
    q = item.quantity
    return q.get('on_hand'), q.get('on_rc'), q.get('on_po')


def test_receiving_moves_stock_and_creates_the_layer_in_one_pending():
    from apps.core.models import Pending
    item, line, out = _received(qty=7, ordered=10)
    assert _stock(item) == (7, 7, 3)
    assert line.inventory_layer.quantity['received'] == 7
    assert line.inventory_layer.serial_batch == line.serial_batch
    add = Pending.objects.get(record_id=str(item.pk), purpose='inventory_line_add',
                              changes__layer__line_id=line.pk)
    assert add.is_processed() and add.changes['layer']['line_id'] == line.pk


def _correct(line, active):
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': active, 'staged': active}
    line.save()
    line.refresh_from_db()


@pytest.mark.usefixtures('chart_of_accounts')
def test_a_received_quantity_corrected_down_moves_the_stock_the_layer_and_the_money():
    """Bill's case, 2026-11-11: converted at 7, meant 5."""
    from apps.accounts.services.journalize import journalize_receipt
    from apps.products.models import InventoryMovement
    item, line, _ = _received(qty=7, ordered=10)
    _correct(line, 5)
    assert _stock(item) == (5, 5, 5), 'on_hand, on_rc and the purchase line all follow'
    assert line.inventory_layer.quantity['received'] == 5
    assert line.inventory_layer.cost['unit_po'] == 4.0, 'the dock cost never changes'
    moves = InventoryMovement.objects.filter(parent_model='receiptline', parent_id=line.pk,
                                             movement_type=InventoryMovement.MOVEMENT_RECEIPT)
    assert sorted(float(m.quantity) for m in moves) == [-2.0, 7.0]
    out = journalize_receipt(line.receipt_id)
    assert out['inventory'] == 20.0, 'the money is the 5 kept, not the 7 first received'
    assert out['payable'] == 20.0 and out['received_not_billed'] == 0.0


def test_a_received_quantity_corrected_up_moves_the_same_layer():
    item, line, _ = _received(qty=7, ordered=10)
    layer_id = line.inventory_layer_id
    _correct(line, 9)
    assert _stock(item) == (9, 9, 1)
    assert line.inventory_layer_id == layer_id and line.inventory_layer.quantity['received'] == 9


def test_a_reduction_past_what_the_layer_holds_is_coached():
    from apps.products.models import InventoryLayer
    item, line, _ = _received(qty=7, ordered=10)
    # 3 of the 7 have left the shelf (an issue against this layer).
    layer = line.inventory_layer
    InventoryLayer.objects.filter(pk=layer.pk).update(quantity={**layer.quantity, 'issued': 3})
    line.quantity = {**line.quantity, 'active': 2, 'staged': 2}
    with pytest.raises(Refused) as refused:
        line.save()
    assert refused.value.code == 'received_already_used'
    assert '3 of the 7' in str(refused.value) and 'count workorder' in str(refused.value)
    _correct(line, 3)
    assert line.inventory_layer.quantity['received'] == 3, 'down to what has left the shelf is fine'


@pytest.mark.usefixtures('chart_of_accounts')
def test_a_journalized_receipt_line_is_not_corrected():
    from apps.accounts.services.journalize import journalize_receipt
    from apps.transactions.models.base_line_model import JournalizedLineError
    item, line, _ = _received(qty=7, ordered=10)
    journalize_receipt(line.receipt_id)
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': 5, 'staged': 5}
    with pytest.raises(JournalizedLineError):
        line.save()
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
    from apps.products.models import Warehouse
    from apps.transactions.models import ReceiptLine
    item, line, _ = _received(qty=7, ordered=10)
    Warehouse.objects.all().update(is_active=False)
    with pytest.raises(ValidationError):
        ReceiptLine.objects.create(receipt=line.receipt, item=line.item, quantity={'active': 2},
                                   cost={'unit': 4.00}, warehouse=None)
    assert _stock(item) == (7, 7, 3)
