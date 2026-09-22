"""Step 5 — flags.not_tracked on every stock path, and the BOM cost it carries.

Bill, 2026-09-22: a non-stocked item (labor, freight estimates) is named by flags.not_tracked,
never by kind. It holds no stock: no Pending moves its buckets, no layer is made for it, and
no rebuild expects a commitment from it. Its cost is the rate in cost.standard, re-read at
rollup, so labor no longer rolls up at $0.
~/Allie/readmes/assessments/2026-09-20/step3-workorders-plan.md §1b.6, §8 step 5
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def _item(ida, not_tracked=False, **cost):
    from apps.products.models import Item
    item = Item.objects.create(ida=ida, name=ida, cost=cost)
    if not_tracked:
        item.is_not_tracked = True
        item.save()
    return item


def _stock_pendings(item):
    from apps.core.models import Pending
    return Pending.objects.filter(model_name='item', record_id=str(item.pk))


def _checks(item):
    from apps.core.services.balance_checker import check_balances
    result = check_balances(scope=('inventory',), item_id=item.pk)
    return {f['check'] for f in result['findings']}


def _order_line(item, qty):
    from apps.transactions.models import Order, OrderLine
    order = Order.objects.create(status='open')
    return OrderLine.objects.create(order=order, item_fk=item, item={'id': item.pk},
                                    quantity={'active': qty}, status='open')


def test_the_delta_builder_moves_nothing_for_a_not_tracked_item():
    from apps.transactions.models.base_line_model import quantity_bucket_deltas
    labor = _item('LABOR-S5', not_tracked=True, standard=45)
    widget = _item('WIDGET-S5')
    assert not any(quantity_bucket_deltas('SO', 5, item=labor).values())
    assert quantity_bucket_deltas('SO', 5, item=widget)['on_so'] == 5


def test_an_order_line_for_labor_writes_no_pending_and_leaves_it_balanced():
    labor = _item('LABOR-S5', not_tracked=True, standard=45)
    line = _order_line(labor, 5)
    assert _stock_pendings(labor).count() == 0
    line.quantity = {'active': 8}
    line.save()                                   # a quantity change moves nothing either
    line.delete()                                 # nor does a delete
    assert _stock_pendings(labor).count() == 0
    labor.refresh_from_db()
    assert not any((labor.quantity or {}).get(b) for b in ('on_hand', 'on_so', 'on_wo'))
    assert 'inventory.not_tracked_stock' not in _checks(labor)


def test_a_stocked_item_still_commits():
    widget = _item('WIDGET-S5')
    _order_line(widget, 5)
    assert _stock_pendings(widget).count() == 1
    widget.refresh_from_db()
    assert float(widget.quantity['on_so']) == 5


def test_receiving_a_not_tracked_item_makes_no_layer():
    from apps.products.models import InventoryLayer
    from apps.transactions.models import Receipt, ReceiptLine
    freight = _item('FREIGHT-S5', not_tracked=True, standard=12)
    receipt = Receipt.objects.create()
    ReceiptLine.objects.create(receipt=receipt, line_number=10, item_fk=freight,
                               item={'id': freight.pk}, quantity={'active': 3},
                               cost={'unit': 12, 'precision': 2})
    assert _stock_pendings(freight).count() == 0
    assert not InventoryLayer.objects.filter(item=freight).exists()


def test_a_rebuild_expects_no_commitment_from_a_not_tracked_item():
    from apps.products.management.commands.rebuild_commitment_buckets import wanted_by_item
    labor = _item('LABOR-S5', not_tracked=True, standard=45)
    _order_line(labor, 5)
    assert labor.pk not in wanted_by_item()


def test_labor_rolls_up_at_its_rate_not_zero():
    from apps.products.models import BillOfMaterial
    kit = _item('KIT-S5')
    part = _item('PART-S5', avg=2, standard=3)
    labor = _item('LABOR-S5', not_tracked=True, avg=0, standard=45)
    BillOfMaterial.objects.create(parent_item=kit, child_item=part, quantity=Decimal('4'))
    hours = BillOfMaterial.objects.create(parent_item=kit, child_item=labor, quantity=Decimal('0.5'))
    assert hours.cost_snapshot == Decimal('45')   # standard, not the $0 avg
    assert BillOfMaterial._rollup_cost(kit.pk, max_depth=1, current_depth=0) == Decimal('30.5')

    # The user changes the rate: labor re-reads it; a stocked part keeps its snapshot.
    labor.cost = {'avg': 0, 'standard': 50}
    labor.save()
    part.cost = {'avg': 9, 'standard': 9}
    part.save()
    assert BillOfMaterial._rollup_cost(kit.pk, max_depth=1, current_depth=0) == Decimal('33')
