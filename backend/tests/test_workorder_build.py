"""Production workorders — one item per line, signed; nothing moves until Complete.

Bill, 2026-09-26/27: three behaviours (no BOM with costs entered; one BOM level; full BOM with a
+/− pair per subassembly); scrap on its own lines; the made item costs what its parts' layers gave.
~/Allie/readmes/assessments/2026-09-26-workorder-window.md

Build 10 Carts. Cart = 4 Wheel + 1 Frame + 0.5 h labor. Wheel = 1 Tire (scrap 0.1) + 1 Rim.
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def _item(name, stock=None, cost='0', not_tracked=False):
    from apps.core.models.pending import Pending
    from apps.products.models import Item, Warehouse
    from apps.products.services.inventory.inventory_layers import create_layer
    item = Item.objects.create(name=name, ida=name.upper(), quantity={'on_hand': 0, 'allocated': 0, 'available': 0},
                               cost={'standard': float(cost)}, flags={'not_tracked': True} if not_tracked else {})
    if stock:
        warehouse = Warehouse.objects.filter(is_active=True).order_by('id').first() \
            or Warehouse.objects.create(code='WH1', name='Main')
        create_layer(item.pk, warehouse.pk, Decimal(stock), Decimal(cost), reason='test stock')
        Pending.objects.create(model_name='item', record_id=str(item.pk), purpose='opening_balance',
                               changes={'on_hand': float(stock)})
    item.refresh_from_db()
    return item


def _bom(parent, child, qty, scrap='0', **op):
    from apps.products.models.bill_of_material import BillOfMaterial
    return BillOfMaterial.objects.create(parent_item=parent, child_item=child, quantity=Decimal(qty),
                                         scrap_factor=Decimal(scrap), op_data=op or {})


@pytest.fixture
def cart():
    from apps.products.models import Warehouse
    Warehouse.objects.create(code='WH1', name='Main')
    items = {
        'cart': _item('Cart'),
        'wheel': _item('Wheel', stock='40', cost='8'),
        'frame': _item('Frame', stock='20', cost='5'),
        'tire': _item('Tire', stock='60', cost='2'),
        'rim': _item('Rim', stock='60', cost='3'),
        'labor': _item('Labor', cost='20', not_tracked=True),
    }
    _bom(items['cart'], items['wheel'], '4')
    _bom(items['cart'], items['frame'], '1')
    _bom(items['cart'], items['labor'], '0.5')
    _bom(items['wheel'], items['tire'], '1', scrap='0.1')
    _bom(items['wheel'], items['rim'], '1')
    return items


def _wo(item, qty, cost=None):
    from apps.transactions.models import WorkOrder, WorkOrderLine
    wo = WorkOrder.objects.create()
    line = WorkOrderLine.objects.create(
        workorder=wo, line_type='build', item={'item_id': item.pk, 'id_num': item.pk}, item_fk_id=item.pk,
        quantity={'active': qty}, cost={'unit': cost} if cost is not None else {})
    return wo, line


def _run(verb, wo, **payload):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    return run_command(Actor(kind='system', source='command'), verb, 'workorder', wo.pk, payload)


def _q(item, leaf='on_hand'):
    item.refresh_from_db()
    return float(item.quantity.get(leaf) or 0)


def _lines(wo):
    from apps.transactions.models import WorkOrderLine
    return list(WorkOrderLine.objects.filter(workorder=wo).order_by('id'))


def _layer_cost(line):
    from apps.products.models.inventory_layer import InventoryLayer
    line.refresh_from_db()
    return float(InventoryLayer.objects.get(pk=line.inventory_layer_id).cost['landed'])


def _balanced(*items):
    from apps.core.services.balance_checker import check_balances
    for item in items:
        findings = check_balances(scope=('inventory',), item_id=item.pk)['findings']
        assert not findings, findings


def test_a_build_commits_on_wo_and_its_parts_commit_nothing(cart):
    wo, line = _wo(cart['cart'], 10)
    assert _q(cart['cart'], 'on_wo') == 10
    _run('expand', wo, line_id=line.pk, depth=1)
    assert _q(cart['wheel'], 'on_wo') == 0 and _q(cart['wheel']) == 40      # a plan holds nothing


def test_case_1_no_bom_the_cost_entered_on_the_line(cart):
    wo, line = _wo(cart['frame'], 3, cost=6.5)
    _run('complete', wo)
    assert _q(cart['frame']) == 23
    assert _layer_cost(line) == 6.5
    assert _q(cart['frame'], 'on_wo') == 0
    _balanced(cart['frame'])


def test_case_2_one_bom_level_costs_from_the_layers_consumed(cart):
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=1)
    types = sorted((l.line_type, l.item_fk_id, float(l.quantity['active'])) for l in _lines(wo))
    assert ('consume', cart['wheel'].pk, -40.0) in types and ('consume', cart['frame'].pk, -10.0) in types
    _run('complete', wo)
    assert (_q(cart['cart']), _q(cart['wheel']), _q(cart['frame'])) == (10, 0, 10)
    # (40 wheels × 8 + 10 frames × 5 + 5 h labor × 20) / 10
    assert _layer_cost(line) == pytest.approx((40 * 8 + 10 * 5 + 5 * 20) / 10)
    _balanced(cart['cart'], cart['wheel'], cart['frame'])


def test_case_3_full_bom_builds_and_uses_the_subassembly_with_its_scrap(cart):
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=0)
    lines = _lines(wo)
    wheel_lines = sorted(l.line_type for l in lines if l.item_fk_id == cart['wheel'].pk)
    assert wheel_lines == ['build', 'consume']                        # a +/− pair
    [scrap] = [l for l in lines if l.line_type == 'scrap']
    assert scrap.item_fk_id == cart['tire'].pk and float(scrap.quantity['active']) == -4.0
    _run('complete', wo)
    assert _q(cart['wheel']) == 40                                    # built 40, used 40: net zero
    assert (_q(cart['tire']), _q(cart['rim'])) == (16, 20)            # 40 + 4 scrap, 40
    wheel_build = next(l for l in lines if l.item_fk_id == cart['wheel'].pk and l.line_type == 'build')
    wheel_unit = (44 * 2 + 40 * 3) / 40                               # scrap goes into the item (Bill)
    assert _layer_cost(wheel_build) == pytest.approx(wheel_unit)
    assert _layer_cost(line) == pytest.approx((40 * wheel_unit + 10 * 5 + 5 * 20) / 10)
    _balanced(cart['cart'], cart['wheel'], cart['tire'], cart['rim'], cart['frame'])


def test_expanding_again_replaces_what_it_made(cart):
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=0)
    _run('expand', wo, line_id=line.pk, depth=1)
    assert len(_lines(wo)) == 1 + 3                                  # the build, wheel, frame, labor


def test_a_completed_build_does_not_change(cart):
    from apps.core.services.door import Refused
    wo, line = _wo(cart['frame'], 3, cost=6.5)
    _run('complete', wo)
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': 4}
    with pytest.raises(Refused) as refused:
        line.save()
    assert refused.value.code == 'workorder_complete'
    with pytest.raises(Refused) as refused:
        _run('complete', wo)
    assert refused.value.code == 'workorder_complete'


def test_a_locked_part_refuses_the_whole_complete(cart):
    from apps.core.services.door import Refused
    from apps.products.models.inventory_layer import InventoryLayer
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=1)
    InventoryLayer.objects.filter(item_id=cart['frame'].pk).update(is_locked=True)
    with pytest.raises(Refused) as refused:
        _run('complete', wo)
    assert refused.value.code == 'item_locked'
    assert (_q(cart['cart']), _q(cart['wheel']), _q(cart['frame'])) == (0, 40, 20)   # nothing moved


def test_a_full_bom_workorder_is_locked_from_normal_editing(cart):
    """Bill, 2026-09-27: full-BOM workorders change only through their commands; one level stays
    editable."""
    from apps.core.services.door import Refused
    from apps.transactions.models import WorkOrderLine
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=0)
    frame = WorkOrderLine.objects.get(workorder=wo, item_fk_id=cart['frame'].pk)
    frame.quantity = {**frame.quantity, 'active': -12}
    with pytest.raises(Refused) as refused:
        frame.save()
    assert refused.value.code == 'full_bom_locked'
    _run('expand', wo, line_id=line.pk, depth=1)                   # expand again, one level
    frame = WorkOrderLine.objects.get(workorder=wo, item_fk_id=cart['frame'].pk)
    frame.quantity = {**frame.quantity, 'active': -12}
    frame.save()                                                   # editable by hand
    _run('complete', wo)                                           # and complete still works
    assert _q(cart['frame']) == 8
