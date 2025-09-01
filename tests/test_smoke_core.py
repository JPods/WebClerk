import pytest
from apps.products.models import Item

pytestmark = [pytest.mark.django_db, pytest.mark.fast, pytest.mark.smoke]


def test_smoke_item_creation_defaults():
    item = Item.objects.create(name="SmokeWidget", kind=Item.KIND_PHYSICAL)
    # Basic assertions: primary key assigned and default JSON structures populated
    assert item.id is not None
    assert isinstance(item.price, dict) and 'currency' in item.price
    assert isinstance(item.cost, dict) and 'currency' in item.cost
    # Ensure save doesn't overwrite user modifications on second save
    item.price['base'] = 42
    item.save()
    item.refresh_from_db()
    assert item.price['base'] == 42
