import json
from pathlib import Path

ACCESS_PATH = Path(__file__).resolve().parent.parent / "common" / "default_access.json"

# Load once at import time
with open(ACCESS_PATH) as f:
    ACCESS_DATA = json.load(f)

def get_allowed_fields(table_name: str, role: str, access_type: str = "view") -> list:
    """
    Returns a list of allowed fields for a given table, role, and access_type ('view' or 'edit').
    """
    for setting in ACCESS_DATA:
        if (
            setting.get("is_active", True)
            and setting.get("purpose") == "view_edit"
            and setting.get("table_name") == table_name
        ):
            role_data = setting["data"].get(role.upper())
            if not role_data:
                # fallback to PUBLIC or empty
                role_data = setting["data"].get("PUBLIC", {})
            return role_data.get(access_type, [])
    return []

def reload_access_data():
    global ACCESS_DATA
    with open(ACCESS_PATH) as f:
        ACCESS_DATA = json.load(f)