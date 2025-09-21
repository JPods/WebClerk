from __future__ import annotations
from typing import Dict, Tuple, Optional
from django.apps import apps
from django.conf import settings
from django.db.models import Model
import re

_KEY_RE = re.compile(r"^[a-z0-9_]+$")

def _normalize_blessed() -> Dict[str, Tuple[str, str]]:
    """
    settings.WCAPI_BLESSED_MODELS:
      { "contact": "core.Contact", "domain": "core.Domain", "order": "transactions.Order", ... }
    Returns: { "contact": ("core","Contact"), ... } with lower-cased keys.
    """
    raw = getattr(settings, "WCAPI_BLESSED_MODELS", {}) or {}
    if not isinstance(raw, dict):
        raise ValueError("WCAPI_BLESSED_MODELS must be a dict of {model_key: 'app.Model'}")
    mapping: Dict[str, Tuple[str, str]] = {}
    for k, dotted in raw.items():
        k_norm = (k or "").strip().lower()
        if not _KEY_RE.match(k_norm):
            raise ValueError(f"Invalid model key '{k}'; use lowercase snake_case [a-z0-9_].")
        if not isinstance(dotted, str) or "." not in dotted:
            raise ValueError(f"Invalid mapping for '{k}'; expected 'app_label.ModelName'.")
        app_label, model_name = dotted.split(".", 1)
        mapping[k_norm] = (app_label, model_name)
    return mapping

_BLESSED: Dict[str, Tuple[str, str]] = _normalize_blessed()

def refresh_from_settings() -> None:
    global _BLESSED
    _BLESSED = _normalize_blessed()

def model_map() -> Dict[str, Tuple[str, str]]:
    return dict(_BLESSED)

def resolve(key: str) -> Optional[type[Model]]:
    """
    Only resolve models explicitly blessed in settings.WCAPI_BLESSED_MODELS.
    key must be the canonical model_name (snake_case) you blessed.
    """
    k = (key or "").strip().lower()
    if not k:
        return None
    entry = _BLESSED.get(k)
    if not entry:
        return None
    app_label, model_name = entry
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None