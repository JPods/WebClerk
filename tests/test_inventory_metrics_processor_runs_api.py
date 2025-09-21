import pytest
from decimal import Decimal
from django.urls import reverse
from django.test import override_settings
from apps.products.models import InventoryLayer
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import PendingInventoryAdjustment
from apps.products.services.inventory_adjustment_processor import process_pending_inventory
from apps.products.models.processor_runs import InventoryAdjustmentProcessorRun

pytestmark = pytest.mark.django_db

def make_stack(qty=10):
    item = Item.objects.create(name="Metrics Item")
    wh = Warehouse.objects.create(name="WH", code=f"W{item.id}")
    return InventoryLayer.objects.create(item=item, warehouse=wh, quantity={"received": float(qty), "issued": 0})


def test_metrics_api_includes_processor_runs(client, django_user_model):
    user = django_user_model.objects.create_user(email="u@example.com", password="p")
    client.login(email="u@example.com", password="p")
    # Create a pending to ensure a processor run will have non-zero attempted
    stack = make_stack(5)
    stack.is_locked = True
    stack.save(update_fields=["is_locked"])
    success, pending = stack.issue_or_enqueue(2)
    assert not success and isinstance(pending, PendingInventoryAdjustment)
    stack.is_locked = False
    stack.save(update_fields=["is_locked"])
    process_pending_inventory(dry_run=False)
    url = '/domain/'
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()['data']
    assert 'processor_runs' in data
    assert data['processor_runs']['latest_global'] is not None


@override_settings(INVENTORY_PROMETHEUS_REQUIRE_AUTH=False)
def test_prometheus_endpoint(client):
    url = '/domain/' + '?auth=0'
    resp = client.get(url)
    assert resp.status_code == 200
    if resp.get('Content-Type','').startswith('application/json'):
        payload = resp.json()
        body = payload.get('data') if isinstance(payload, dict) else ''
    else:
        body = resp.content.decode()
    body = body or ""
    assert 'inventory_reservations_active_reserved_qty' in str(body)
