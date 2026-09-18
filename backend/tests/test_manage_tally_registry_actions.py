import uuid
from datetime import date, datetime, time, timezone

import pytest
from django.contrib.auth import get_user_model

from apps.transactions.models.invoice import Invoice


pytestmark = pytest.mark.django_db


def _create_user(role: str = "staff"):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"{role}_tally_registry_{suffix}",
        email=f"{role}_tally_registry_{suffix}@example.com",
        password="pw12345",
        name_first=role.capitalize(),
        name_last="Tester",
        role=role,
    )


def _ms(d: date) -> int:
    return int(datetime.combine(d, time.min, tzinfo=timezone.utc).timestamp() * 1000)


def test_get_tally_report_registry_lists_named_reports(client):
    user = _create_user("staff")
    client.force_login(user)

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "get_tally_report_registry",
            "params": {},
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    keys = {r["report_key"] for r in payload["reports"]}
    assert "tally_summary_by_period" in keys
    assert "tally_sales_by_customer_year" in keys
    assert "tally_inventory_usage_by_month" in keys


def test_execute_tally_report_by_key(client):
    user = _create_user("staff")
    client.force_login(user)

    invoice = Invoice.objects.create(totals={"total": 120.0})
    invoice.dt_created = _ms(date(2026, 3, 10))
    invoice.save(update_fields=["dt_created"])

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "execute_tally_report",
            "params": {
                "report_key": "tally_summary_by_period",
                "report_params": {
                    "start_date": "2026-03-01",
                    "end_date": "2026-03-31",
                },
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    payload = body["data"]
    assert payload["report_key"] == "tally_summary_by_period"
    assert payload["result"]["totals"]["count"] >= 1


def test_export_tally_report_csv(client):
    user = _create_user("staff")
    client.force_login(user)

    invoice = Invoice.objects.create(totals={"total": 220.0})
    invoice.dt_created = _ms(date(2026, 4, 10))
    invoice.save(update_fields=["dt_created"])

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "export_tally_report",
            "params": {
                "report_key": "tally_summary_by_period",
                "format": "csv",
                "report_params": {
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-30",
                },
                "columns": ["model_name", "count", "total"],
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    assert payload["format"] == "csv"
    assert payload["filename"].endswith(".csv")
    assert "model_name,count,total" in payload["content"]
    assert payload["row_count"] >= 1
