"""D02 (Bill, 2026-09-21): one landed-cost engine.

Each landed cost spreads by its own basis (value default, weight, quantity) over the
lines the user has not pinned; pins must add up to the header amount; and the result
reaches the inventory layer, so stock is carried at what we owe.
~/Allie/readmes/assessments/2026-09-20/defects/D02-allocations-method-dead.md
"""
from __future__ import annotations

import pytest

from tests.utils import received_receipt_line
from django.core.exceptions import ValidationError

from apps.transactions.models import Receipt, ReceiptLine

pytestmark = pytest.mark.django_db


def _receipt(method=None, **landed):
    alloc = {'freight': 0, 'duty': 0, 'handling': 0, 'vat': 0,
             'method': {'freight': 'value', 'duty': 'value', 'handling': 'value', 'vat': 'value'}}
    alloc.update(landed)
    alloc['method'].update(method or {})
    return Receipt.objects.create(allocations=alloc)


def _line(receipt, n, qty, unit, **extra):
    cost = {'unit': unit, 'precision': 2}
    cost.update(extra.pop('cost', {}))
    return received_receipt_line(receipt=receipt, line_number=n, quantity={'active': qty},
                                      cost=cost, **extra)


def _shares(receipt, comp):
    return [l.totals['landed'][comp] for l in receipt.lines.order_by('line_number')]


def test_value_is_the_default_and_the_money_ties():
    r = _receipt(freight=10, duty=4, handling=3)
    _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    r.refresh_from_db()
    assert _shares(r, 'freight') == [4.57, 5.43]
    assert r.totals['total'] == 109.00
    assert [d['basis_used'] for d in r.metadata['landed_decisions']['components']] == ['value'] * 4


def test_quantity_is_honoured_when_the_record_asks_for_it():
    r = _receipt(method={'freight': 'quantity'}, freight=10)
    _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    r.refresh_from_db()
    assert _shares(r, 'freight') == [6.36, 3.64]          # D02's table: not 4.57 / 5.43


def test_each_component_keeps_its_own_basis():
    r = _receipt(method={'freight': 'weight', 'duty': 'value'}, freight=10, duty=4)
    _line(r, 10, 7, 6.00, physical={'weight': {'value': 1, 'unit': 'kg'}})
    _line(r, 20, 4, 12.50, physical={'weight': {'value': 5, 'unit': 'kg'}})
    r.refresh_from_db()
    assert _shares(r, 'freight') == [2.59, 7.41]          # 7 kg / 20 kg
    assert _shares(r, 'duty') == [1.83, 2.17]             # 42 / 50 by value


def test_a_missing_weight_falls_back_to_value_and_says_so():
    r = _receipt(method={'freight': 'weight'}, freight=10)
    _line(r, 10, 7, 6.00, physical={'weight': {'value': 1, 'unit': 'kg'}})
    _line(r, 20, 4, 12.50)
    r.refresh_from_db()
    assert _shares(r, 'freight') == [4.57, 5.43]
    freight = r.metadata['landed_decisions']['components'][0]
    assert (freight['basis'], freight['basis_used']) == ('weight', 'value')
    assert 'line 20' in freight['reason']


def _pin(line, **pins):
    line.cost = {**line.cost, 'landed_override': pins}
    line.save()


def test_a_pinned_share_stands_and_the_rest_takes_the_remainder():
    r = _receipt(freight=10)
    a = _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    _pin(a, freight=8.00)
    r.refresh_from_db()
    assert _shares(r, 'freight') == [8.00, 2.00]
    assert r.totals['total'] == 102.00


def test_pins_that_exceed_the_header_are_refused():
    r = _receipt(freight=10)
    a = _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    with pytest.raises(ValidationError, match='pin 12'):
        _pin(a, freight=12.00)


def test_every_line_pinned_must_add_to_the_header():
    r = _receipt(freight=10)
    a = _line(r, 10, 7, 6.00)
    b = _line(r, 20, 4, 12.50)
    _pin(a, freight=4.00)
    with pytest.raises(ValidationError, match='Every line pins'):
        _pin(b, freight=5.00)


def test_one_word_for_every_component_is_refused():
    r = Receipt.objects.create(allocations={'freight': 10, 'method': 'value'})
    with pytest.raises(ValidationError, match='not a single word'):
        _line(r, 10, 1, 1.00)


def _planned_line(receipt, n, qty, unit, item, warehouse):
    return ReceiptLine.objects.create(receipt=receipt, line_number=n, item_fk=item, item={'id': item.pk},
                                      quantity={'active': 0, 'staged': qty}, warehouse=warehouse,
                                      cost={'unit': unit, 'precision': 2})


def test_the_landed_cost_is_fixed_on_the_layer_when_received():
    """Bill, 2026-09-28/30: the layer is born at the receipt's landed cost and never changes."""
    from apps.core.models.pending import Pending
    from apps.core.services.door import Refused
    from apps.products.models import Item, Warehouse
    from apps.transactions.services.receive_commands import receive_receipt
    item, other = Item.objects.create(name='D02 item'), Item.objects.create(name='D02 other')
    wh = Warehouse.objects.create(name='D02 WH', code='D02WH')
    r = _receipt(freight=10, duty=4)
    first = _planned_line(r, 10, 7, 6.00, item, wh)
    _planned_line(r, 20, 4, 12.50, other, wh)
    receive_receipt(r)
    first.refresh_from_db()
    layer = first.inventory_layer
    # freight 4.57 / 7 = 0.6529, duty 1.83 / 7 = 0.2614
    assert layer.cost['unit_po'] == 6.00
    assert layer.cost['freight'] == 0.6529
    assert layer.cost['duty'] == 0.2614
    assert layer.cost['landed'] == pytest.approx(6.00 + 0.6529 + 0.2614)

    r.refresh_from_db()
    r.allocations = {**r.allocations, 'freight': 0}
    with pytest.raises(Refused) as refused:
        r.save()
    assert refused.value.code == 'layer_cost_fixed'
    layer.refresh_from_db()
    assert layer.cost['freight'] == 0.6529, 'a layer never changes'
    assert not Pending.objects.filter(purpose='inventory_cost_change').exists()
