import uuid
from datetime import date, datetime, time, timezone

import pytest
from django.contrib.auth import get_user_model

from apps.core.models.setting import Setting
from apps.products.models import InventoryLayer, InventoryMovement, Item, Warehouse


pytestmark = pytest.mark.django_db


def _create_user(role: str = "staff"):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"{role}_inv_tally_{suffix}",
        email=f"{role}_inv_tally_{suffix}@example.com",
        password="pw12345",
        name_first=role.capitalize(),
        name_last="Tester",
        role=role,
    )


def _ms(d: date) -> int:
    return int(datetime.combine(d, time.min, tzinfo=timezone.utc).timestamp() * 1000)


def _movement(*, item: Item, warehouse: Warehouse, movement_type: str, dt: date, quantity: float, landed_cost: float = 0.0):
    layer = InventoryLayer.objects.create(
        item=item,
        warehouse=warehouse,
        quantity={"received": max(quantity, 0), "issued": 0, "scrapped": 0},
        cost={"landed": landed_cost, "moving_avg": landed_cost, "unit_po": landed_cost},
    )
    movement = InventoryMovement.objects.create(
        item=item,
        warehouse=warehouse,
        inventory_layer=layer,
        movement_type=movement_type,
        quantity=quantity,
        reason="test",
    )
    movement.dt_created = _ms(dt)
    movement.save(update_fields=["dt_created"])
    return movement


def test_manage_tally_inventory_usage_by_month(client):
    user = _create_user("staff")
    client.force_login(user)

    item = Item.objects.create(name="Widget A", sku="WIDGET-A")
    warehouse = Warehouse.objects.create(name="Main", code="MAIN")

    _movement(item=item, warehouse=warehouse, movement_type="receipt", dt=date(2026, 2, 1), quantity=10, landed_cost=5)
    _movement(item=item, warehouse=warehouse, movement_type="issue", dt=date(2026, 2, 5), quantity=3, landed_cost=5)
    _movement(item=item, warehouse=warehouse, movement_type="adjust", dt=date(2026, 2, 9), quantity=-1, landed_cost=5)

    before = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_inventory_usage_by_month viewed",
        parent_model="report",
    ).count()

    resp = client.post(
        "/wcapi/manage/",
        data={
            "action": "get_tally_inventory_usage_by_month",
            "params": {
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    rows = payload["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["item_name"] == "Widget A"
    assert row["month"] == "2026-02"
    assert row["receipt_qty"] == 10.0
    assert row["issue_qty"] == 3.0
    assert row["adjust_qty"] == -1.0
    assert row["net_qty"] == 6.0
    assert row["receipt_value"] == 50.0
    assert row["issue_value"] == 15.0
    assert row["adjust_value"] == -5.0
    assert row["net_value"] == 30.0

    after = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_inventory_usage_by_month viewed",
        parent_model="report",
    ).count()
    assert after == before + 1


def test_manage_tally_inventory_yearly_summary(client):
    user = _create_user("staff")
    client.force_login(user)

    item = Item.objects.create(name="Widget B", sku="WIDGET-B")
    warehouse = Warehouse.objects.create(name="Overflow", code="OVERFLOW")

    _movement(item=item, warehouse=warehouse, movement_type="receipt", dt=date(2025, 1, 2), quantity=20, landed_cost=4)
    _movement(item=item, warehouse=warehouse, movement_type="issue", dt=date(2025, 7, 7), quantity=5, landed_cost=4)
    _movement(item=item, warehouse=warehouse, movement_type="issue", dt=date(2025, 9, 7), quantity=-2, landed_cost=4)

    resp = client.post(
        "/wcapi/manage/",
        data={
            "action": "get_tally_inventory_yearly_summary",
            "params": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    rows = payload["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["item_name"] == "Widget B"
    assert row["year"] == 2025
    assert row["receipt_qty"] == 20.0
    assert row["usage_qty"] == 3.0
    assert row["adjust_qty"] == 0.0
    assert row["net_qty"] == 17.0
    assert row["usage_value"] == 12.0
    assert row["net_value"] == 68.0
    assert payload["totals"]["count"] == 3
