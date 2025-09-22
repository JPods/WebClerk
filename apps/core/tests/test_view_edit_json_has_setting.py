import json
from pathlib import Path
from django.conf import settings

def test_view_edit_json_includes_setting_record():
    path = Path(getattr(settings, "VIEW_EDIT_JSON_PATH"))
    assert path.exists(), f"VIEW_EDIT_JSON_PATH missing: {path}"
    text = path.read_text()
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("//")]
    data = json.loads("\n".join(lines))
    assert isinstance(data, list)
    models = { (rec or {}).get("model_name") for rec in data }
    assert "setting" in models, "Expected a 'setting' model record in view_edit.json"