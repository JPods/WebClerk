import pytest
from django.utils import timezone

from apps.core.models.report import Report
from apps.support.scheduler.tasks import task_cleanup_metadata_temp


pytestmark = pytest.mark.django_db


def _now_ms() -> int:
    return int(timezone.now().timestamp() * 1000)


def test_metadata_temp_add_and_expire_helpers():
    report = Report.objects.create(name="TempTest", model_name="report")

    now_ms = _now_ms()
    report.add_temp_entry(
        kind="hint",
        snippet="keep me",
        clear_dt=now_ms + 86_400_000,
        source="alice",
    )
    report.add_temp_entry(
        kind="hint",
        snippet="expire me",
        clear_dt=now_ms - 1,
        source="alice",
    )
    report.save(update_fields=["metadata"])

    report.refresh_from_db()
    assert len(report.get_temp_entries()) == 2

    removed = report.clear_expired_temp_entries(now_ms=now_ms)
    assert removed == 1
    report.save(update_fields=["metadata"])

    report.refresh_from_db()
    remaining = report.get_temp_entries()
    assert len(remaining) == 1
    assert remaining[0]["snippet"] == "keep me"


def test_task_cleanup_metadata_temp_prunes_expired_entries(monkeypatch):
    now_ms = _now_ms()

    stale = Report.objects.create(name="StaleTemp", model_name="report")
    stale.add_temp_entry(
        kind="hint",
        snippet="stale",
        clear_dt=now_ms - 5_000,
        source="alice",
    )
    stale.save(update_fields=["metadata"])

    fresh = Report.objects.create(name="FreshTemp", model_name="report")
    fresh.add_temp_entry(
        kind="hint",
        snippet="fresh",
        clear_dt=now_ms + 5_000_000,
        source="alice",
    )
    fresh.save(update_fields=["metadata"])

    monkeypatch.setattr(
        "apps.support.scheduler.tasks.apps.get_models",
        lambda: [Report],
    )

    result = task_cleanup_metadata_temp.run(limit_per_model=10000)
    assert result["status"] == "ok"
    assert result["changed_records"] >= 1
    assert result["removed_entries"] >= 1
    assert result["model_stats"].get("core.Report", {}).get("changed", 0) >= 1

    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert len(stale.get_temp_entries()) == 0
    assert len(fresh.get_temp_entries()) == 1
