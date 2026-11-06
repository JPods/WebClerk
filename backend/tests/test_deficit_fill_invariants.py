"""An adversarial read of filling inventory deficits for wrong totals (plan 102, the lead's
item 4b, 2026-11-06). Invariants: a receipt fills the oldest shortage first and only what it
has; what a deficit still lacks is its quantity less every fill and settlement, whichever
path wrote it; a layer never issues more than it received; the fills and the stock add up."""
from decimal import Decimal

import pytest

from tests.test_deficit_fill import _complete_vendor, _deficit, _item, _receive, _run   # noqa: F401 — the helpers
from tests.test_stock_layers_follow_sales import _invoice, _line

pytestmark = pytest.mark.django_db


def _deficits(item):
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    return list(Pending.objects.filter(purpose=DEFICIT_PURPOSE, record_id=str(item.pk)).order_by('id'))


def _layers(item):
    from apps.products.models.inventory_layer import InventoryLayer
    return list(InventoryLayer.objects.filter(item_id=item.pk).order_by('id'))


def test_a_receipt_fills_the_oldest_shortage_first_and_only_what_it_has(chart_of_accounts):
    item = _item('3.00')
    first, second = _invoice(), _invoice()
    _line(first, item, 3)                      # 3 short
    _line(second, item, 4)                     # 4 more short
    a, b = _deficits(item)
    assert (a.incremental_remaining('deficit_qty'), b.incremental_remaining('deficit_qty')) == (3, 4)

    _receive(item, 5, 4.0)                     # 5 arrive: the first shortage closes, the second takes 2
    a, b = _deficits(item)
    assert a.dt_processed and a.incremental_remaining('deficit_qty') == 0
    assert not b.dt_processed and b.incremental_remaining('deficit_qty') == 2
    layer, = _layers(item)
    assert float(layer.remaining_qty()) == 0.0   # all five issued to the shortages
    item.refresh_from_db()
    assert float(item.quantity['on_hand']) == -2.0        # on hand is received less shipped: the open shortage reads negative

    _receive(item, 10, 4.0)                    # 10 more: the second closes, 8 stay on the shelf
    a, b = _deficits(item)
    assert b.dt_processed and b.incremental_remaining('deficit_qty') == 0
    assert [float(l.remaining_qty()) for l in _layers(item)] == [0.0, 8.0]
    item.refresh_from_db()
    assert float(item.quantity['on_hand']) == 8.0


def test_a_settlement_and_a_fill_count_against_the_same_remaining(chart_of_accounts):
    from apps.products.services.inventory.inventory_layers import settle_deficit
    item = _item('3.00')
    invoice = _invoice()
    _line(invoice, item, 5)                    # 5 short
    assert settle_deficit(item.pk, Decimal('2')) == Decimal('0')          # 2 settled elsewhere, nothing left over
    d, = _deficits(item)
    assert d.incremental_remaining('deficit_qty') == 3
    assert settle_deficit(item.pk, Decimal('10')) == Decimal('7')         # 3 settle, 7 left over
    d, = _deficits(item)
    assert d.dt_processed and d.incremental_remaining('deficit_qty') == 0
    _receive(item, 4, 4.0)                     # nothing left to fill: all four stay on the shelf
    layer, = _layers(item)
    assert float(layer.remaining_qty()) == 4.0


def test_the_fills_the_movements_and_the_stock_agree(chart_of_accounts):
    from apps.products.models.inventory_layer import InventoryMovement
    item = _item('3.00')
    invoice = _invoice()
    _line(invoice, item, 3)
    receipt = _receive(item, 10, 4.0)
    fills = InventoryMovement.objects.filter(item_id=item.pk, reason__startswith='Fills shortage')
    assert [float(m.quantity) for m in fills] == [-3.0]
    assert all(m.metadata['deficit_fill']['unit_cost'] == 3.0 and m.metadata['deficit_fill']['qty'] == 3.0 for m in fills)
    layer, = _layers(item)
    q = layer.quantity or {}
    assert (float(q.get('received') or 0), float(q.get('issued') or 0)) == (10.0, 3.0)
    assert float(layer.remaining_qty()) == 7.0
    assert float(layer.remaining_qty()) + sum(-float(m.quantity) for m in fills) == 10.0   # the layer never issues more than it received
