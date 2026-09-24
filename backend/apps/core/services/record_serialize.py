from __future__ import annotations
import json
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple
from django.forms.models import model_to_dict
from django.db.models import Model, QuerySet
from apps.core.utils import registry, policy

def to_dict(obj: Model, *, allow: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    data = model_to_dict(obj)
    
    # Explicitly add fields that model_to_dict might miss
    # (id, ida, and other non-editable or special fields)
    for field in obj._meta.get_fields():
        name = getattr(field, 'name', None)
        if name and name not in data:
            try:
                value = getattr(obj, name, None)
                # Skip reverse relations, callables, and related model instances
                if not callable(value) and not hasattr(value, 'all') and not isinstance(value, Model):
                    data[name] = value
            except Exception:
                pass
    
    # Include computed properties declared by the model (e.g., Contact.phone, .address_full, .domain)
    for prop_name in getattr(obj, 'COMPUTED_FIELDS', []):
        if prop_name not in data:
            try:
                data[prop_name] = getattr(obj, prop_name, None)
            except Exception:
                pass

    # Expand FK fields listed in EXPAND_FK_FIELDS → {id, ida, name} for display
    for fk_name in getattr(obj, 'EXPAND_FK_FIELDS', []):
        fk_id = data.get(fk_name)
        if fk_id and isinstance(fk_id, int):
            try:
                related_obj = getattr(obj, fk_name, None)
                if related_obj and isinstance(related_obj, Model):
                    data[fk_name] = {
                        'id': related_obj.pk,
                        'ida': getattr(related_obj, 'ida', ''),
                        'name': getattr(related_obj, 'display_name', '') or str(related_obj),
                    }
            except Exception:
                pass

    # Ensure key fields are always present
    if 'id' not in data:
        data['id'] = getattr(obj, 'pk', None) or getattr(obj, 'id', None)
    if 'ida' not in data and hasattr(obj, 'ida'):
        data['ida'] = getattr(obj, 'ida', None)
    if 'duration' not in data and hasattr(obj, 'duration'):
        data['duration'] = getattr(obj, 'duration', None)
    if 'percent_complete' not in data and hasattr(obj, 'percent_complete'):
        data['percent_complete'] = getattr(obj, 'percent_complete', None)
    if 'project_ida' not in data and hasattr(obj, 'project_ida'):
        data['project_ida'] = getattr(obj, 'project_ida', None)
    if 'dt_start' not in data and hasattr(obj, 'dt_start'):
        data['dt_start'] = getattr(obj, 'dt_start', None)
    
    filtered = {k: data.get(k) for k in allow} if allow else data

    field_map = {}
    try:
        field_map = {f.name: f for f in obj._meta.get_fields() if getattr(f, "name", None)}
    except Exception:
        pass

    json_field_names = set()
    for name, field in field_map.items():
        kind = ""
        if hasattr(field, "get_internal_type"):
            try:
                kind = (field.get_internal_type() or "")
            except Exception:
                kind = ""
        if "JSON" in kind.upper():
            json_field_names.add(name)

    schema_keys = sorted(k for k in filtered.keys() if k not in json_field_names)
    json_keys = sorted(k for k in filtered.keys() if k in json_field_names)

    ordered: Dict[str, Any] = {}
    for key in schema_keys:
        ordered[key] = filtered[key]
    for key in json_keys:
        ordered[key] = filtered[key]
    return ordered

def filter_input_fields(ModelCls: type[Model], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Filter payload to only include fields that exist on the model.

    Accepts both ``f.name`` (e.g. ``customer``) **and** ``f.attname``
    (e.g. ``customer_id``) so callers can send either the FK object-name
    or the raw column-name.  For ForeignKey fields the value is always
    stored under the ``attname`` (``customer_id``) so that ``setattr``
    uses the raw-column path and avoids Django's FK descriptor which
    expects a model instance.
    """
    meta_fields = getattr(ModelCls._meta, "fields", [])
    # Build lookup: accepted key → canonical key (attname for FKs)
    allowed: Dict[str, str] = {}
    for f in meta_fields:
        attname = getattr(f, "attname", None)
        if attname and attname != f.name:
            # ForeignKey: accept both forms, but store under attname
            allowed[f.name] = attname
            allowed[attname] = attname
        else:
            allowed[f.name] = f.name
    result: Dict[str, Any] = {}
    for k, v in (payload or {}).items():
        canonical = allowed.get(k)
        if canonical is not None:
            # Later key wins (e.g. customer_id overrides customer)
            result[canonical] = v
    return result

def get_queryset(model_key: str, *, actor) -> Tuple[type[Model], QuerySet]:
    ModelCls = registry.resolve(model_key or "")
    if not ModelCls:
        raise ValueError("invalid model")

    # Prefer the project's active() queryset when available so wcapi/get
    # naturally hides soft-deleted / inactive rows.
    try:
        active = getattr(ModelCls.objects, "active", None)
        qs = active() if callable(active) else ModelCls.objects.all()
    except Exception:
        qs = ModelCls.objects.all()

    normalized_key = (model_key or "").replace("_", "").lower()
    # Prefetch lines for transaction models
    if normalized_key in {'quote', 'order', 'invoice', 'purchase', 'workorder'}:
        qs = qs.prefetch_related('lines')

    qs = policy.inject_constraints(qs, actor=actor, model_key=model_key)
    return ModelCls, qs

def visible_queryset(model_key: str, *, actor) -> Tuple[type[Model], QuerySet]:
    """The rows a reader may see, in one call, so no caller has to remember a filter.

    The one read channel (Bill, 2026-09-23). Three gates: security_level (access.level_q),
    the role's block, and the role's id scope (both in inject_role_filters). An anonymous
    visitor passes gate 1 at level 1 and reaches only the models the public role lists.
    """
    from apps.core.services import access
    from apps.core.services.door import as_actor
    from apps.core.services.role_filter import inject_role_filters

    actor = as_actor(actor)
    if actor.kind == 'public':
        ModelCls = registry.resolve(model_key or "")
        if not ModelCls:
            raise ValueError("invalid model")
        if not access.public_fields(model_key):
            return ModelCls, ModelCls.objects.none()
        return ModelCls, ModelCls.objects.filter(access.level_q(actor), is_active=True)

    ModelCls, qs = get_queryset(model_key, actor=actor)
    if not actor.is_guarded:
        return ModelCls, qs
    if any(f.name == 'security_level' for f in ModelCls._meta.concrete_fields):
        qs = qs.filter(access.level_q(actor))
    qs = qs.filter(inject_role_filters(actor, model_key))
    # A person always reaches their own contact, role or none (Bill, 2026-09-23). What they
    # may change on it is still the edit enumeration and the contact account guard —
    # authority fields (role, is_superuser, security_level) stay refused.
    if access.model_key(model_key) == 'contact' and actor.user_id:
        from django.db.models import Q
        qs = ModelCls.objects.filter(Q(pk__in=qs.values('pk')) | Q(pk=actor.user_id))
    return ModelCls, qs

def get_item(model_key: str, *, request, id: Any) -> Optional[Model]:
    from apps.core.services.door import Actor
    ModelCls, qs = visible_queryset(model_key, actor=Actor.from_request(request))
    try:
        obj = qs.get(pk=id)
        # Force refresh from database to get latest data
        obj.refresh_from_db()
        return obj
    except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
        return None

def list_items(model_key: str, *, request, filters: Optional[Dict[str, Any]] = None, limit: int = 500, ordering: Optional[str] = None) -> List[Model]:
    from apps.core.services.door import Actor
    ModelCls, qs = visible_queryset(model_key, actor=Actor.from_request(request))
    if filters:
        qs = qs.filter(**filters)
    if ordering:
        qs = qs.order_by(ordering)
    return list(qs[:limit])


