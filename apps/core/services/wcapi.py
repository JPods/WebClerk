from __future__ import annotations
import json
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple
from django.forms.models import model_to_dict
from django.db.models import Model, QuerySet
from apps.core.utils import registry, policy

def to_dict(obj: Model, *, allow: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    data = model_to_dict(obj)
    filtered = {k: data.get(k) for k in allow} if allow else data
    return filtered

def filter_input_fields(ModelCls: type[Model], payload: Dict[str, Any]) -> Dict[str, Any]:
    fields = {f.name for f in getattr(ModelCls._meta, "fields", [])}
    return {k: v for k, v in (payload or {}).items() if k in fields}

def get_queryset(model_key: str, *, request) -> Tuple[type[Model], QuerySet]:
    ModelCls = registry.resolve(model_key or "")
    if not ModelCls:
        raise ValueError("invalid model")
    qs = ModelCls.objects.all()
    qs = policy.inject_constraints(qs, request=request, model_key=model_key)
    return ModelCls, qs

def get_item(model_key: str, *, request, id: Any) -> Optional[Model]:
    ModelCls, qs = get_queryset(model_key, request=request)
    try:
        return qs.get(pk=id)
    except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
        return None

def list_items(model_key: str, *, request, filters: Optional[Dict[str, Any]] = None, limit: int = 500, ordering: Optional[str] = None) -> List[Model]:
    ModelCls, qs = get_queryset(model_key, request=request)
    if filters:
        qs = qs.filter(**filters)
    if ordering:
        qs = qs.order_by(ordering)
    return list(qs[:limit])

def save_item(model_key: str, *, request, data: Dict[str, Any], id: Any = None) -> Tuple[Any, str]:
    ModelCls, qs = get_queryset(model_key, request=request)
    clean = filter_input_fields(ModelCls, data)
    if id is not None:
        obj = qs.filter(pk=id).first()
        if obj is None:
            raise LookupError("not found")
        for k, v in clean.items():
            setattr(obj, k, v)
        obj.save()
        return obj.pk, "updated"
    obj = ModelCls.objects.create(**clean)
    return obj.pk, "created"

def delete_item(model_key: str, *, request, id: Any) -> bool:
    ModelCls, qs = get_queryset(model_key, request=request)
    obj = qs.filter(pk=id).first()
    if not obj:
        return False
    obj.delete()
    return True