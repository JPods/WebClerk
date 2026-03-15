import uuid
from datetime import date, datetime, time, timezone

import pytest
from django.contrib.auth import get_user_model

from apps.core.models.setting import Setting
from apps.orgs.models import OrgBase, OrgType
from apps.transactions.models.invoice import Invoice


pytestmark = pytest.mark.django_db


def _create_user(role: str = "staff"):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"{role}_tally_dim_{suffix}",
        email=f"{role}_tally_dim_{suffix}@example.com",
        password="pw12345",
        name_first=role.capitalize(),
        name_last="Tester",
        role=role,
    )


def _ms(d: date) -> int:
    return int(datetime.combine(d, time.min, tzinfo=timezone.utc).timestamp() * 1000)


def _create_invoice_with_date(*, dt: date, customer_id: int | None = None, manufacturer_id: int | None = None, total: float = 0.0):
    invoice = Invoice.objects.create(
        customer_id=customer_id,
        manufacturer_id=manufacturer_id,
        totals={"total": total},
    )
    # CoreModel.save sets dt_created to now on first save, so set explicit fixture date afterward.
    invoice.dt_created = _ms(dt)
    invoice.save(update_fields=["dt_created"])
    return invoice


def test_manage_tally_sales_by_customer_month(client):
    user = _create_user("staff")
    client.force_login(user)

    customer_a = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Customer A")
    customer_b = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Customer B")

    _create_invoice_with_date(customer_id=customer_a.id, dt=date(2026, 3, 5), total=100.0)
    _create_invoice_with_date(customer_id=customer_a.id, dt=date(2026, 3, 20), total=25.5)
    _create_invoice_with_date(customer_id=customer_b.id, dt=date(2026, 2, 15), total=300.0)

    before = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_sales_by_customer_month viewed",
        parent_model="report",
    ).count()

    resp = client.post(
        "/wcapi/manage/",
        data={
            "action": "get_tally_sales_by_customer_month",
            "params": {
                "start_date": "2026-02-01",
                "end_date": "2026-03-31",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    rows = payload["rows"]
    assert len(rows) >= 2

    target = [r for r in rows if r["dimension_name"] == "Customer A" and r["month"] == "2026-03"]
    assert target
    assert target[0]["count"] == 2
    assert target[0]["total"] >= 125.5

    assert payload["totals"]["count"] >= 3
    assert payload["totals"]["total"] >= 425.5

    after = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_sales_by_customer_month viewed",
        parent_model="report",
    ).count()
    assert after == before + 1


def test_manage_tally_sales_by_manufacturer_month(client):
    user = _create_user("staff")
    client.force_login(user)

    manufacturer_a = OrgBase.objects.create(org_type=OrgType.MANUFACTURER, display_name="Manufacturer A")

    _create_invoice_with_date(manufacturer_id=manufacturer_a.id, dt=date(2026, 1, 11), total=40.0)
    _create_invoice_with_date(manufacturer_id=manufacturer_a.id, dt=date(2026, 1, 19), total=60.0)

    resp = client.post(
        "/wcapi/manage/",
        data={
            "action": "get_tally_sales_by_manufacturer_month",
            "params": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    rows = payload["rows"]
    assert len(rows) >= 1

    target = [r for r in rows if r["dimension_name"] == "Manufacturer A" and r["month"] == "2026-01"]
    assert target
    assert target[0]["count"] == 2
    assert target[0]["total"] >= 100.0
    assert payload["totals"]["count"] >= 2
    assert payload["totals"]["total"] >= 100.0


def test_manage_tally_sales_by_customer_year(client):
    user = _create_user("staff")
    client.force_login(user)

    customer_a = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Customer YoY")

    _create_invoice_with_date(customer_id=customer_a.id, dt=date(2025, 3, 5), total=80.0)
    _create_invoice_with_date(customer_id=customer_a.id, dt=date(2026, 4, 5), total=125.0)
    _create_invoice_with_date(customer_id=customer_a.id, dt=date(2026, 7, 5), total=25.0)

    before = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_sales_by_customer_year viewed",
        parent_model="report",
    ).count()

    resp = client.post(
        "/wcapi/manage/",
        data={
            "action": "get_tally_sales_by_customer_year",
            "params": {
                "start_date": "2025-01-01",
                "end_date": "2026-12-31",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    rows = payload["rows"]
    current = [r for r in rows if r["dimension_name"] == "Customer YoY" and r["year"] == 2026]
    prior = [r for r in rows if r["dimension_name"] == "Customer YoY" and r["year"] == 2025]

    assert current
    assert prior
    assert current[0]["total"] == 150.0
    assert current[0]["previous_total"] == 80.0
    assert current[0]["delta"] == 70.0
    assert current[0]["count"] == 2
    assert prior[0]["total"] == 80.0
    assert prior[0]["previous_total"] == 0.0

    after = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_sales_by_customer_year viewed",
        parent_model="report",
    ).count()
    assert after == before + 1
