from __future__ import annotations

from typing import Dict, Optional, Tuple
from django.apps import apps as django_apps

# Optional, lightweight cache
_MODEL_CACHE: Dict[str, object] = {}

def _normalize(s: str) -> str:
    return (s or "").strip().strip("/").lower()

def _singularize(s: str) -> str:
    # naive singularization to help map "domains" -> "domain"
    s = _normalize(s)
    if s.endswith("ies"):
        return s[:-3] + "y"
    if s.endswith("ses"):
        return s[:-2]
    if s.endswith("s"):
        return s[:-1]
    return s

def _find_model_by_name(model_name: str):
    """
    Scan installed models and return the first class whose model_name matches.
    """
    target = _normalize(model_name)
    for m in django_apps.get_models():
        if m._meta.model_name == target:
            return m
    return None

def _resolve_dotpath(key: str):
    """
    Allow "app_label.ModelName" or "app_label.modelname".
    """
    key = _normalize(key)
    if "." not in key:
        return None
    app_label, _, model_part = key.partition(".")
    # Try exact class-style first
    cls = django_apps.get_model(app_label, model_part, require_ready=False)
    if cls:
        return cls
    # Try normalized model_name
    for m in django_apps.get_app_config(app_label).get_models():
        if m._meta.model_name == model_part:
            return m
    return None

def get_model(model_key: str):
    """
    Resolve a model class from a slug:
      - "domain" -> communications.Domain (by model_name)
      - "contact" -> core.Contact (swapped auth user)
      - "app_label.ModelName" or "app_label.modelname"
      - Plural slugs like "domains" -> "domain"
    """
    key = _normalize(model_key)
    if not key:
        return None
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    # 1) Dotpath "app_label.ModelName"
    cls = _resolve_dotpath(key)
    if cls:
        _MODEL_CACHE[key] = cls
        return cls

    # 2) Exact model_name
    cls = _find_model_by_name(key)
    if cls:
        _MODEL_CACHE[key] = cls
        return cls

    # 3) Singularized fallback
    skey = _singularize(key)
    if skey != key:
        cls = _find_model_by_name(skey)
        if cls:
            _MODEL_CACHE[key] = cls
            return cls

    return None

def to_model_name(model_cls) -> Optional[str]:
    try:
        return model_cls._meta.model_name
    except Exception:
        return None

def normalize_table_key(k: str) -> str:
    return _normalize(k)

def _discover_allowed_keys():
    keys = set()
    for m in django_apps.get_models():
        mn = m._meta.model_name
        keys.add(mn)
        # add simple plural alias
        if not mn.endswith("s"):
            if mn.endswith("y"):
                keys.add(mn[:-1] + "ies")
            elif mn.endswith("s"):
                keys.add(mn + "es")
            else:
                keys.add(mn + "s")
    return sorted(keys)

ALLOWED_TABLE_KEYS = _discover_allowed_keys()
