"""Consuming stock: never wait on a lock, and record a shortage as a deficit.

Defect B-6 (2026-09-23): _consume took select_for_update() without nowait, so a build
waited behind another save's transaction; and a shortfall made a synthetic layer
(received = issued = the shortfall) that hid the shortage inside the layers. Now a
locked item or layer is a 409 layer_locked, and a shortfall is an open
inventory_deficit Pending — the record check_balances already reads.
"""
from decimal import Decimal

import pytest

from apps.core.services.door import Refused
from tests.conftest import ItemFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


def _stocked(qty='5', cost='2.00'):
    from apps.products.services.inventory.inventory_layers import create_layer
    item = ItemFactory()
    wh = WarehouseFactory()
    layer = create_layer(item.pk, wh.pk, Decimal(qty), Decimal(cost))
    return item, layer


def test_a_shortfall_is_an_open_deficit_pending_not_a_synthetic_layer():
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    from apps.products.models.inventory_layer import InventoryLayer
    from apps.products.services.inventory.inventory_layers import consume_fifo

    item, _ = _stocked('5')
    layers_before = InventoryLayer.objects.filter(item=item).count()

    consume_fifo(item.pk, Decimal('8'))

    assert InventoryLayer.objects.filter(item=item).count() == layers_before, \
        "no invented layer"
    deficit = Pending.objects.get(purpose=DEFICIT_PURPOSE, record_id=str(item.pk))
    assert deficit.dt_processed == 0, "it stays open until receipts fill it"
    assert deficit.incremental_remaining('deficit_qty') == Decimal('3')


def test_enough_stock_records_no_deficit():
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    from apps.products.services.inventory.inventory_layers import consume_fifo

    item, _ = _stocked('5')
    consume_fifo(item.pk, Decimal('5'))
    assert not Pending.objects.filter(purpose=DEFICIT_PURPOSE, record_id=str(item.pk)).exists()


def test_a_locked_layer_is_a_409_to_retry_not_a_wait():
    from apps.core.models.pending import LayerLocked
    from apps.products.services.inventory.inventory_layers import consume_fifo

    item, layer = _stocked('5')
    layer.is_locked = True
    layer.save(update_fields=['is_locked'])

    with pytest.raises(LayerLocked) as caught:
        consume_fifo(item.pk, Decimal('1'))

    assert isinstance(caught.value, Refused), "the door answers it with its code"
    assert caught.value.status == 409 and caught.value.code == 'layer_locked'
    assert caught.value.details['item_id'] == item.pk
    assert 'try again' in caught.value.message
