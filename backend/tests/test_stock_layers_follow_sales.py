"""Layers follow every sale — plan §16b/§16d (Bill, 2026-09-26).

An invoice line's change is a Pending; its applier moves the item and the layers together.
More sold consumes by the item's costing method; less sold gives back to the layers that line
took from, newest first, at the costs it took them at; a negative line is a return, landing in
a layer of its own at the item's average cost. A short sale is recorded (an open deficit), not
refused. What the layers gave is the line's event: its cost of goods.
~/Allie/readmes/assessments/2026-09-24-one-route-per-verb.md §16b, §16c, §16d
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def _stocked(method=None, layers=((5, '1.00'), (5, '2.00'), (5, '3.00'))):
    """An item with on_hand 15 in three layers costing 1, 2 and 3, oldest first."""
    from apps.core.models.pending import Pending
    from apps.products.models import Item, Warehouse
    from apps.products.services.inventory.inventory_layers import create_layer
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'allocated': 0, 'available': 0},
                               config={'costing_method': method} if method else {})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    total = Decimal('0')
    for qty, cost in layers:
        create_layer(item.pk, warehouse.pk, Decimal(qty), Decimal(cost), reason='test stock')
        total += Decimal(qty)
    # The item's on_hand arrives the only way it moves: an applied Pending. The layers were
    # made above, so this increase names none (fixture state).
    Pending.objects.create(model_name='item', record_id=str(item.pk), purpose='opening_balance',
                           changes={'on_hand': float(total)})
    item.refresh_from_db()
    return item, warehouse


def _invoice(**header):
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Invoice
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    return Invoice.objects.create(customer_id=buyer.pk, finance={'sales_tax_rate': 0}, **header)


def _line(invoice, item, active, **extra):
    from apps.transactions.models import InvoiceLine
    return InvoiceLine.objects.create(
        invoice=invoice, item={'item_id': item.pk, 'id_num': item.pk, 'description': item.name},
        quantity={'active': active}, price={'unit': 10, 'precision': 2}, cost={'unit': 0}, **extra)


def _set(line, active):
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': active}
    line.save()


def _issued(item):
    from apps.products.models.inventory_layer import InventoryLayer
    return [float((layer.quantity or {}).get('issued') or 0)
            for layer in InventoryLayer.objects.filter(item_id=item.pk).order_by('id')]


def _on_hand(item):
    item.refresh_from_db()
    return float(item.quantity['on_hand'])


def _shelf(item):
    from apps.products.models.inventory_layer import InventoryLayer
    return float(sum(Decimal(str(layer.remaining_qty()))
                     for layer in InventoryLayer.objects.filter(item_id=item.pk)))


def _open_deficit(item):
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    return float(sum(p.incremental_remaining('deficit_qty') for p in
                     Pending.objects.filter(purpose=DEFICIT_PURPOSE, record_id=str(item.pk), dt_processed=0)))


def _consumed(line):
    line.refresh_from_db()
    return [e['consumed'] for e in line.events if isinstance(e, dict) and e.get('consumed')]


def _balanced(item):
    """The invariant check_balances holds: Σ layer remaining − open deficit == on_hand."""
    return _shelf(item) - _open_deficit(item) == _on_hand(item)


def test_a_sale_consumes_fifo_and_records_its_cost_of_goods():
    item, _ = _stocked()
    line = _line(_invoice(), item, 7)
    assert _on_hand(item) == 8
    assert _issued(item) == [5, 2, 0]
    [consumed] = _consumed(line)
    assert [(e['qty'], e['unit_cost']) for e in consumed['layers']] == [(5, 1.0), (2, 2.0)]
    assert consumed['cost'] == 9.0 and consumed['short'] == 0
    assert _balanced(item)


def test_lifo_takes_the_newest_layer_first():
    item, _ = _stocked(method='lifo')
    _line(_invoice(), item, 7)
    assert _issued(item) == [0, 2, 5]


def test_selling_more_consumes_more_and_selling_less_gives_back_newest_first():
    item, _ = _stocked()
    line = _line(_invoice(), item, 7)          # 5 from layer 1, 2 from layer 2
    _set(line, 9)                              # 2 more from layer 2
    assert _issued(item) == [5, 4, 0]
    _set(line, 4)                              # 5 back: 4 to layer 2, then 1 to layer 1
    assert _issued(item) == [4, 0, 0]
    assert _on_hand(item) == 11
    assert _balanced(item)


def test_deleting_a_sale_gives_everything_back():
    item, _ = _stocked()
    line = _line(_invoice(), item, 12)
    line.delete()
    assert _issued(item) == [0, 0, 0]
    assert _on_hand(item) == 15
    assert _balanced(item)


def test_a_short_sale_is_recorded_not_refused_and_giving_back_settles_the_shortfall_first():
    item, _ = _stocked()
    line = _line(_invoice(), item, 20)
    assert _on_hand(item) == -5
    assert _issued(item) == [5, 5, 5]
    assert _open_deficit(item) == 5
    assert _balanced(item)
    _set(line, 17)                             # 3 back: the shelf never had them
    assert _open_deficit(item) == 2
    assert _issued(item) == [5, 5, 5]
    assert _balanced(item)


def test_a_return_lands_in_a_layer_of_its_own_at_average_cost():
    item, warehouse = _stocked()
    item.refresh_from_db()
    average = item.cost['avg']                 # (5·1 + 5·2 + 5·3) / 15 = 2
    line = _line(_invoice(shipping={'warehouse_id': warehouse.pk}), item, -3)
    assert _on_hand(item) == 18
    [consumed] = _consumed(line)
    [back] = consumed['layers']
    assert back['return'] and back['qty'] == -3 and back['unit_cost'] == average
    from apps.products.models.inventory_layer import InventoryLayer
    layer = InventoryLayer.objects.get(pk=back['layer_id'])
    assert layer.warehouse_id == warehouse.pk and float(layer.quantity['received']) == 3
    assert _balanced(item)


def test_a_smaller_return_takes_its_own_layer_back_down():
    item, warehouse = _stocked()
    line = _line(_invoice(shipping={'warehouse_id': warehouse.pk}), item, -3)
    _set(line, -1)
    assert _on_hand(item) == 16
    assert _balanced(item)


def test_a_return_with_several_warehouses_and_none_named_is_refused_coached():
    from apps.core.services.door import Refused
    from apps.products.models import Warehouse
    item, _ = _stocked()
    Warehouse.objects.create(code='WH2', name='Second')
    with pytest.raises(Refused) as refused:
        _line(_invoice(), item, -3)
    assert refused.value.code == 'warehouse_required'


def test_a_sale_is_consumed_once_however_often_its_pending_is_tried():
    from apps.core.models.pending import Pending
    item, _ = _stocked()
    line = _line(_invoice(), item, 7)
    p = Pending.objects.get(purpose='inventory_line_add', config__line_id=line.pk,
                            config__line_model='invoiceline')
    assert p.changes['consumed']['cost'] == 9.0          # saved with the Pending
    p.try_apply()
    Pending.objects.get(pk=p.pk).try_apply()
    assert _issued(item) == [5, 2, 0]
    assert len(_consumed(line)) == 1
