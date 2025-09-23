from __future__ import annotations
from typing import Dict, Any

def seed_default_connections(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"created": [], "updated": [], "skipped": []}