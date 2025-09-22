from __future__ import annotations
from typing import Iterable, Optional
from django.db.models import QuerySet, Model

try:
    from apps.core.wcapi.model_policies import read_allowlist as _mp_read_allowlist
except Exception:
    _mp_read_allowlist = None

def inject_constraints(qs: QuerySet, *, request, model_key: str) -> QuerySet:
    # TODO: enforce role/tenant/publish/reserved rules via Settings
    return qs

def field_allowlist(model, request=None):
    """
    Existing API used across the project. If model policies are enabled,
    return their resolved read allowlist; else keep legacy behavior.
    """
    if _mp_read_allowlist:
        allow = _mp_read_allowlist(model, request=request)
        if allow is not None:
            return allow
    # Optional: restrict outbound fields by role/settings
    # fall back to prior static/default logic
    return None