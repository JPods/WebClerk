import json
from pathlib import Path
from django.conf import settings

def _load_json():
    path = Path(getattr(settings, "VIEW_EDIT_JSON_PATH"))
    text = path.read_text()
    data = json.loads("\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("//")))
    return { (rec or {}).get("model_name"): rec for rec in data if isinstance(rec, dict) }

def test_contact_has_compact_view_profile():
    by_model = _load_json()
    contact = by_model.get("contact")
    assert contact, "missing contact record"
    meta = (contact.get("data") or {}).get("__meta__") or {}
    views = meta.get("views") or {}
    assert "compact" in views, "expected a 'compact' view profile"
    prof = views["compact"]
    assert (prof.get("pagination") or {}).get("page_size") == 5
    assert "fields" in prof and "view" in prof["fields"], "compact profile should define fields.view"