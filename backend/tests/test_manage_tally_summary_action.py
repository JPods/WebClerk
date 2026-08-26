import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models.setting import Setting
from apps.transactions.models.invoice import Invoice
from apps.transactions.models.order import Order


pytestmark = pytest.mark.django_db


def _create_user(role: str = "staff"):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"{role}_tally_{suffix}",
        email=f"{role}_tally_{suffix}@example.com",
        password="pw12345",
        name_first=role.capitalize(),
        name_last="Tester",
        role=role,
    )


def test_manage_tally_summary_by_period_success(client):
    user = _create_user("staff")
    client.force_login(user)

    before_logs = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_summary_by_period viewed",
        parent_model="report",
    ).count()

    Invoice.objects.create(totals={"total": 120.25})
    Order.objects.create(totals={"total": 80.75})

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "get_tally_summary_by_period",
            "params": {},
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    assert "start_date" in payload
    assert "end_date" in payload
    assert isinstance(payload.get("rows"), list)
    assert isinstance(payload.get("totals"), dict)

    rows_by_model = {r["model_name"]: r for r in payload["rows"]}
    assert "invoice" in rows_by_model
    assert "order" in rows_by_model
    assert rows_by_model["invoice"]["count"] >= 1
    assert rows_by_model["order"]["count"] >= 1
    assert payload["totals"]["total"] >= 201.0

    after_logs = Setting.objects.filter(
        purpose="alice_log",
        role="user_interaction",
        name="get_tally_summary_by_period viewed",
        parent_model="report",
    ).count()
    assert after_logs == before_logs + 1


def test_manage_tally_summary_by_period_invalid_dates(client):
    user = _create_user("staff")
    client.force_login(user)

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "get_tally_summary_by_period",
            "params": {
                "start_date": "2026-05-01",
                "end_date": "2026-04-01",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == "fail"
    assert body["error"]["code"] == "invalid_params"
