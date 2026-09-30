"""Layers and movements name the line that caused them (GL-by-layer step 2; Bill 2026-09-28/30).

Ratchet: a layer or movement that names a parent names a row that exists, by the door's model key.
Opening layers have no parent until step 6 turns them into an opening count workorder.
"""
from decimal import Decimal

import pytest

from tests.conftest import ItemFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


def _resolves(model_key, pk):
    from apps.core.services.door import resolve_model
    model_cls, _, _ = resolve_model(model_key)
    return model_cls.objects.filter(pk=pk).exists()


def test_a_layer_and_its_movement_carry_their_parent():
    from apps.products.models.inventory_layer import InventoryMovement
    from apps.products.services.inventory.inventory_layers import create_layer, consume_fifo
    item, wh = ItemFactory(), WarehouseFactory()
    layer = create_layer(item.pk, wh.pk, Decimal('4'), Decimal('3.00'),
                         parent_model='inventorylayer', parent_id=None)
    consume_fifo(item.pk, Decimal('1'), parent_model='inventorylayer', parent_id=layer.pk)
    moves = InventoryMovement.objects.filter(inventory_layer=layer).order_by('id')
    assert [m.movement_type for m in moves] == ['receipt', 'issue']
    assert moves[1].parent_model == 'inventorylayer' and moves[1].parent_id == layer.pk
    assert all(m.dt_journaled == 0 for m in moves)


def test_every_named_parent_resolves():
    from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement
    for Model in (InventoryLayer, InventoryMovement):
        for model_key, pk in (Model.objects.exclude(parent_model='')
                              .values_list('parent_model', 'parent_id')):
            assert pk is not None and _resolves(model_key, pk), (Model.__name__, model_key, pk)
