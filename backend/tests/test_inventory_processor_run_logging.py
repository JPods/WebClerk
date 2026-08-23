import pytest
from decimal import Decimal
from apps.core.models import Pending
from apps.products.models import InventoryLayer
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.transactions.services.pending_inventory_processor import process_pending_for_item

pytestmark = pytest.mark.django_db


def make_item_and_stack(qty=10):
    item = Item.objects.create(name="Test Item", quantity={
        'on_hand': float(qty), 'available': float(qty),
        'on_so': 0, 'on_po': 0, 'on_p': 0,
    })
    wh = Warehouse.objects.create(name="Main WH", code=f"WH{item.id}")
    stack = InventoryLayer.objects.create(
        item=item, warehouse=wh,
        quantity={"received": float(qty), "issued": 0},
    )
    return item, stack


def test_pending_applies_on_save():
    item, stack = make_item_and_stack(qty=100)
    p = Pending.objects.create(
        model_name='item', record_id=str(item.pk),
        purpose='inventory_line_add', name='Test apply',
        changes={'on_p': 15, 'item_id': item.pk},
    )
    assert p.is_processed()
    item.refresh_from_db()
    assert item.quantity.get('on_p') == 15


def test_celery_processor_picks_up_unprocessed():
    item, stack = make_item_and_stack(qty=100)

    # Create pending and force it to unprocessed
    p = Pending.objects.create(
        model_name='item', record_id=str(item.pk),
        purpose='inventory_line_add', name='Test celery',
        changes={'on_so': 9, 'item_id': item.pk},
    )
    # Reset: force unprocessed and revert item
    Pending.objects.filter(pk=p.pk).update(dt_processed=0)
    item.quantity['on_so'] = 0
    item.save(update_fields=['quantity'])

    result = process_pending_for_item(item_id=item.pk)
    assert result['processed'] == 1

    item.refresh_from_db()
    assert item.quantity.get('on_so') == 9
