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

    # Prefetch lines for transaction models
    if model_key in ['proposal', 'salesorder', 'purchaseorder']:
        qs = qs.prefetch_related('lines')

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

    # Create the object
    obj = ModelCls.objects.create(**clean)

    # Auto-link newly created communication records to a Contact (if present)
    try:
        from common.refs.links import ensure_bidirectional
        from common.models import LINK_DENORMALIZE_FIELDS
        from apps.core.models import Contact

        comm_models = {"email", "phone", "address", "location", "domain"}
        if model_key and model_key.lower() in comm_models:
            # Determine the bucket name used in refs.links (back-compat: address -> location)
            bucket = "location" if model_key.lower() in ("address", "location") else model_key.lower()

            # Resolve contact id from payload or authenticated user
            contact = None
            contact_id = None
            if isinstance(data, dict):
                # common variations
                contact_id = data.get("contact_id") or data.get("contactId") or (data.get("contact") if isinstance(data.get("contact"), (int, str)) else None)
                try:
                    if isinstance(contact_id, (str,)):
                        contact_id = int(contact_id)
                except Exception:
                    contact_id = None
            # Fallback to authenticated request user when available
            user = getattr(request, "user", None)
            if not contact_id and user and getattr(user, "is_authenticated", False):
                # The project uses Contact as the auth user model in most places
                if getattr(user, "__class__", None) and getattr(user, "_meta", None) and getattr(user._meta, "model_name", None) == "contact":
                    contact = user
            if contact_id:
                contact = Contact.objects.filter(pk=contact_id).first()

            if contact:
                # Build denormalized object from LINK_DENORMALIZE_FIELDS
                fields = LINK_DENORMALIZE_FIELDS.get(bucket, ["id"]) or ["id"]
                denorm = {f: getattr(obj, f, None) for f in fields}
                # Ensure refs.links shaped correctly
                refs = getattr(contact, "refs", {}) or {}
                links = refs.get("links") or {}
                bucket_list = links.get(bucket) or []

                # Replace existing entry with same id (dict or int) to avoid dupes, else append
                existing_found = False
                for idx, it in enumerate(list(bucket_list)):
                    if isinstance(it, dict) and it.get("id") == getattr(obj, "pk"):
                        bucket_list[idx] = denorm
                        existing_found = True
                        break
                    if isinstance(it, int) and it == getattr(obj, "pk"):
                        bucket_list[idx] = denorm
                        existing_found = True
                        break
                if not existing_found:
                    bucket_list.append(denorm)

                links[bucket] = bucket_list
                refs["links"] = links
                contact.refs = refs
                # Persist contact refs with minimal update fields
                contact.save(update_fields=["refs", "dt_modified", "version"])                

                # Also ensure the created object's refs.links.contact contains the contact id
                try:
                    if not isinstance(getattr(obj, "refs", None), dict):
                        obj.refs = {}
                    obj_links = obj.refs.setdefault("links", {})
                    contact_list = obj_links.setdefault("contact", [])
                    if contact.pk not in contact_list:
                        contact_list.append(contact.pk)
                        obj.save(update_fields=["refs"])
                except Exception:
                    pass

                # Also ensure a lightweight bidirectional link entry exists for quick lookup
                try:
                    ensure_bidirectional(contact, obj, kind="contact")
                except Exception:
                    # Non-fatal if link helper fails
                    pass
    except Exception:
        # Defensive: do not block creation on linking errors
        pass

    return obj.pk, "created"

def delete_item(model_key: str, *, request, id: Any) -> bool:
    ModelCls, qs = get_queryset(model_key, request=request)
    obj = qs.filter(pk=id).first()
    if not obj:
        return False
    obj.delete()
    return True