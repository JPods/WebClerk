"""Every executable report runs.

One test, not six. The reports are records in a registry, so the test walks the
registry rather than naming reports one at a time — register a seventh and it is
covered the same day, with no test to remember to add.

The second test is the rule Bill set for the whole system: an installation that
can run nothing has not failed, it has not been given them yet. It asks
WC_HQ, and if HQ cannot be reached it falls back to the set this release ships.
Either way the caller gets a list.
"""
import secrets
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models.report import Report
from apps.core.services import installation_init
from apps.core.services.report_registry import (
    REPORT_PURPOSE_EXECUTABLE, SHIPPED_REPORTS, list_executable_reports)

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)

pytestmark = pytest.mark.django_db


def _staff():
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"staff_report_{suffix}",
        email=f"staff_report_{suffix}@example.com",
        password=TEST_PASSWORD,
        name_first="Staff",
        name_last="Tester",
        role="staff",
    )


def _manage(client, action, params=None):
    return client.post(
        "/wcapi/_manage/",
        data={"action": action, "params": params or {}},
        content_type="application/json",
    )


def test_every_registered_report_executes(client):
    """The registry lists them; each one runs and answers the envelope."""
    client.force_login(_staff())

    listing = _manage(client, "get_report_registry")
    assert listing.status_code == 200
    body = listing.json()
    assert body["status"] == "success"

    reports = body["data"]["reports"]
    assert reports, "the registry listed no executable reports"
    assert body["data"]["count"] == len(reports)

    for entry in reports:
        resp = _manage(client, "execute_report",
                       {"report_key": entry["report_key"],
                        "report_params": entry.get("default_params") or {}})
        assert resp.status_code == 200, (
            f"{entry['report_key']} answered HTTP {resp.status_code}")
        payload = resp.json()
        assert payload["status"] == "success", (
            f"{entry['report_key']}: {payload.get('error')}")
        assert payload["data"]["report_key"] == entry["report_key"]
        assert "result" in payload["data"]

        # Alice sees every report run — that is her primary learning signal.
        assert Report.objects.filter(
            purpose=REPORT_PURPOSE_EXECUTABLE,
            config__report_key=entry["report_key"]).exists()


def test_an_installation_with_no_executable_reports_gets_them(monkeypatch):
    """No definitions is not a failure. Ask HQ; fall back to what we ship."""
    Report.objects.filter(purpose=REPORT_PURPOSE_EXECUTABLE).delete()
    init_bundle.reset_asked()

    # WC_HQ unreachable and no shipped bundle on disk — the hardest case.
    monkeypatch.setattr(init_bundle, "fetch_from_hq",
                        lambda *a, **k: (None, "WC_HQ unreachable: test"))
    monkeypatch.setattr(init_bundle, "load_from_disk",
                        lambda *a, **k: (None, "no shipped bundle"))

    result = list_executable_reports()

    assert result["count"] == len(SHIPPED_REPORTS)
    assert {r["report_key"] for r in result["reports"]} == {
        e["report_key"] for e in SHIPPED_REPORTS}
    assert Report.objects.filter(purpose=REPORT_PURPOSE_EXECUTABLE).count() == len(SHIPPED_REPORTS)
