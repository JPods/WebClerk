"""GET products/inventory/layers: an item's cost layers for the Layers and Counts panels.
dt_ fields are UTC epoch ms (Axiom 14); the view once called .isoformat() on one and
answered 500 for every item with a layer (found 2026-10-27, panel rework)."""
import secrets

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.products.models import InventoryLayer
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse

pytestmark = pytest.mark.django_db

TEST_PASSWORD = secrets.token_urlsafe(16)


def test_layers_answer_with_epoch_dates(django_user_model):
    user = django_user_model.objects.create_superuser(email='layers-view@example.com', password=TEST_PASSWORD)
    token = RefreshToken.for_user(user)
    token['role'] = 'admin'
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    item = Item.objects.create(name='Layered', quantity={'on_hand': 5.0})
    wh = Warehouse.objects.create(name='Main WH', code=f'LV{item.id}')
    InventoryLayer.objects.create(item=item, warehouse=wh, quantity={'received': 5.0, 'issued': 0})

    resp = client.get('/wcapi/products/inventory/layers/', {'item_id': item.id})

    assert resp.status_code == 200, resp.content
    [layer] = resp.json()['data']
    assert layer['remaining'] == 5.0
    assert isinstance(layer['dt_created'], int)
