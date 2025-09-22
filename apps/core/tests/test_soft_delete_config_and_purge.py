import json
from pathlib import Path
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.apps import apps as django_apps

from apps.core.models import Setting
SoftDeleteLedger = django_apps.get_model(Setting._meta.app_label, "SoftDeleteLedger")

def _load_json():
    path = Path(getattr(settings, "VIEW_EDIT_JSON_PATH"))
    assert path.exists(), f"VIEW_EDIT_JSON_PATH missing: {path}"
    text = path.read_text()
    data = json.loads("\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("//")))
    assert isinstance(data, list)
    return { (rec or {}).get("model_name"): rec for rec in data if isinstance(rec, dict) }

@pytest.mark.django_db
def test_soft_delete_meta_present_for_all_but_pending():
    by_model = _load_json()
    assert "pending" in by_model, "Missing 'pending'"
    for name, rec in by_model.items():
        data = rec.get("data") or {}
        meta = data.get("__meta__") or {}
        sd = meta.get("soft_delete")
        if name == "pending":
            assert not sd, "pending must NOT have soft_delete meta"
        else:
            assert sd and sd.get("enabled") is True, f"{name} must enable soft_delete"
            assert int(sd.get("retention_days") or 0) == 60, f"{name} must set retention_days=60"

@pytest.mark.django_db
def test_purge_soft_deleted_removes_objects_due():
    # Create a simple Setting row to purge
    s = Setting.objects.create(
        is_active=True,
        name="to_purge",
        purpose="view_edit",
        role="all",
        model_name="setting",
        data={},
        comment="test"
    )
    # Schedule purge in the past (simulate soft delete)
    purge_at = timezone.now() - timedelta(days=1)
    entry = SoftDeleteLedger.objects.create(
        content_type=ContentType.objects.get_for_model(Setting),
        object_id=s.id,
        purge_at=purge_at,
    )
    assert Setting.objects.filter(pk=s.id).exists()

    call_command("purge_soft_deleted")

    assert not Setting.objects.filter(pk=s.id).exists(), "Setting should be hard-deleted by purge"
    assert not SoftDeleteLedger.objects.filter(pk=entry.pk).exists(), "Ledger entry should be removed"