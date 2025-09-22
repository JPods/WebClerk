import json
from pathlib import Path
from django.conf import settings

def _load_json():
    path = Path(getattr(settings, "VIEW_EDIT_JSON_PATH"))
    text = path.read_text()
    return { (rec or {}).get("model_name"): rec for rec in json.loads("\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("//"))) }

def test_contact_has_keyword_and_open_query_policy():
    by_model = _load_json()
    rec = by_model.get("contact")
    assert rec, "missing contact"
    meta = (rec.get("data") or {}).get("__meta__") or {}
    search = meta.get("search") or {}
    kw = search.get("keywords") or {}
    assert kw.get("type") in {"array","text"}
    if kw.get("type") == "array":
        assert kw.get("field"), "keywords.field is required when type=array"

    q = meta.get("query") or {}
    assert q.get("allow_joins") is not None
    assert isinstance(q.get("allow_ops"), list) or isinstance(q.get("allow_ops"), set)
    assert int(q.get("max_rows") or 0) >= 1