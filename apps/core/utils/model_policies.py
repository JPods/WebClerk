from __future__ import annotations
from typing import Dict, Iterable, List, Optional, Type
from importlib import import_module

from django.conf import settings
from django.db.models import Model

from apps.core.services import wcapi as services
from apps.core.utils.policy import field_allowlist as base_policy


def _get_model_key(model: Type[Model]) -> str:
    return getattr(model._meta, "model_name", model.__name__).lower()


def _get_policies() -> Dict[str, dict]:
    return getattr(settings, "WCAPI_MODEL_POLICIES", {}) or {}


def _enabled() -> bool:
    return bool(getattr(settings, "WCAPI_POLICIES_ENABLED", False))


def _roles_for(request) -> List[str]:
    # Simple role resolution; customize as needed
    roles: List[str] = []
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        roles.append("anonymous")
        return roles
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        roles.append("admin")
    # Add Django group names as roles
    try:
        roles.extend(list(user.groups.values_list("name", flat=True)))
    except Exception:
        pass
    # Fallback default role
    roles.append("user")
    return roles


def _resolve_fields(rule: dict, roles: Iterable[str]) -> Optional[List[str]]:
    if not rule:
        return None
    by_role = (rule or {}).get("by_role") or {}
    # First match wins (admin-first ordering because we push admin first)
    for r in roles:
        v = by_role.get(r)
        if v:
            return list(v)
    default = (rule or {}).get("default")
    return list(default) if default else None


def read_allowlist(model: Type[Model], request=None) -> Optional[List[str]]:
    if not _enabled():
        # fall back to existing policy behavior
        return base_policy(model, request=request)
    cfg = _get_policies().get(_get_model_key(model)) or {}
    fields_cfg = (cfg.get("fields") or {}).get("read") or {}
    roles = _roles_for(request)
    resolved = _resolve_fields(fields_cfg, roles)
    if resolved == ["*"]:
        return None  # None => all fields
    return resolved


def write_allowlist(model: Type[Model], request=None) -> Optional[List[str]]:
    if not _enabled():
        return None  # defer to existing logic; wcapi will validate writes
    cfg = _get_policies().get(_get_model_key(model)) or {}
    fields_cfg = (cfg.get("fields") or {}).get("write") or {}
    roles = _roles_for(request)
    resolved = _resolve_fields(fields_cfg, roles)
    if resolved == ["*"]:
        return None
    return resolved


def sanitize_payload(data: dict, allow: Optional[List[str]]) -> dict:
    if not allow or allow == ["*"]:
        return dict(data or {})
    return {k: v for k, v in (data or {}).items() if k in allow}


def serialize_with_relations(obj: Model, request=None) -> dict:
    model = obj.__class__
    base_allow = read_allowlist(model, request=request)
    payload = services.to_dict(obj, allow=base_allow)

    if not _enabled():
        return payload

    cfg = _get_policies().get(_get_model_key(model)) or {}
    rels = cfg.get("relations") or {}
    for name, spec in rels.items():
        typ = (spec.get("type") or "").lower()
        fields = spec.get("fields") or None
        limit = int(spec.get("limit") or 0) or None

        try:
            if typ == "fk":
                rel_obj = getattr(obj, name, None)
                payload[name] = services.to_dict(rel_obj, allow=fields) if rel_obj else None
            elif typ == "reverse":
                # Discover reverse manager; use custom name if provided
                manager = getattr(obj, name, None)
                if manager is None:
                    # try Django auto reverse name (best-effort)
                    # fallback to scanning first reverse to this model name if needed
                    manager = getattr(obj, f"{model._meta.model_name}_set", None)
                if manager is not None and hasattr(manager, "all"):
                    qs = manager.all()
                    if limit:
                        qs = qs[:limit]
                    payload[name] = [services.to_dict(x, allow=fields) for x in qs]
        except Exception:
            # Do not fail serialization on relation errors
            continue
    return payload


def _import_callable(path: str):
    mod, _, attr = path.rpartition(".")
    fn = getattr(import_module(mod), attr)
    if not callable(fn):
        raise TypeError(f"{path} is not callable")
    return fn


def run_hook(model: Type[Model], hook_name: str, context: dict):
    if not _enabled():
        return
    cfg = _get_policies().get(_get_model_key(model)) or {}
    hooks = cfg.get("hooks") or {}
    path = hooks.get(hook_name)
    if not path:
        return
    try:
        fn = _import_callable(path)
        fn(context)
    except Exception:
        # Hooks are non-fatal by default
        return