import pytest
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

# Cache to avoid repeated filesystem scans
_VIEW_EDIT_JSON_CACHED = None

@pytest.fixture
def api_client(db):
    User = get_user_model()
    user = User.objects.create_user(
        username="apitester",
        email="apitester@example.com",
        password="pw12345",
        name_first="API",
        name_last="Tester",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture(autouse=True)
def ensure_view_edit_json_path():
    global _VIEW_EDIT_JSON_CACHED
    if getattr(settings, "VIEW_EDIT_JSON_PATH", None):
        return
    if _VIEW_EDIT_JSON_CACHED:
        settings.VIEW_EDIT_JSON_PATH = str(_VIEW_EDIT_JSON_CACHED)
        return

    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / "apps" / "core" / "view_edit.json",
        root / "apps" / "core" / "wcapi" / "view_edit.json",
        root / "apps" / "core" / "configs" / "view_edit.json",
        root / "configs" / "view_edit.json",
        root / "config" / "view_edit.json",
        root / "view_edit.json",
    ]
    found = next((p for p in candidates if p.exists()), None)
    if not found:
        # Fallback: search a few common bases
        for base in [root, root / "apps", root / "apps" / "core"]:
            try:
                for p in base.rglob("view_edit.json"):
                    found = p
                    break
            except Exception:
                continue
            if found:
                break
    if found:
        _VIEW_EDIT_JSON_CACHED = found
        settings.VIEW_EDIT_JSON_PATH = str(found)