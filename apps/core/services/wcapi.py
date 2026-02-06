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
                # Skip reverse relations and callables
                if not callable(value) and not hasattr(value, 'all'):
                    data[name] = value
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
    fields = {f.name for f in getattr(ModelCls._meta, "fields", [])}
    return {k: v for k, v in (payload or {}).items() if k in fields}

def get_queryset(model_key: str, *, request) -> Tuple[type[Model], QuerySet]:
    ModelCls = registry.resolve(model_key or "")
    if not ModelCls:
        raise ValueError("invalid model")
    qs = ModelCls.objects.all()

    normalized_key = (model_key or "").replace("_", "").lower()
    # Prefetch lines for transaction models
    if normalized_key in {'proposal', 'salesorder', 'invoice', 'purchaseorder', 'workorder'}:
        qs = qs.prefetch_related('lines')

    qs = policy.inject_constraints(qs, request=request, model_key=model_key)
    return ModelCls, qs

def get_item(model_key: str, *, request, id: Any) -> Optional[Model]:
    ModelCls, qs = get_queryset(model_key, request=request)
    try:
        obj = qs.get(pk=id)
        # Force refresh from database to get latest data
        obj.refresh_from_db()
        return obj
    except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
        return None

def list_items(model_key: str, *, request, filters: Optional[Dict[str, Any]] = None, limit: int = 500, ordering: Optional[str] = None) -> List[Model]:
    ModelCls, qs = get_queryset(model_key, request=request)
    if filters:
        qs = qs.filter(**filters)
    if ordering:
        qs = qs.order_by(ordering)
    return list(qs[:limit])

def save_item(model_key: str, *, request, data: Dict[str, Any], id: Any = None) -> Tuple[Any, str, bool]:
    ModelCls, qs = get_queryset(model_key, request=request)
    clean = filter_input_fields(ModelCls, data)
    if isinstance(clean.get("refs"), dict):
        try:
            from common.refs.contact_refs import normalize_refs_for_save
            clean["refs"] = normalize_refs_for_save(clean["refs"])
        except Exception:
            pass

    # Prevent non-privileged users from elevating roles/privileges on Contact records
    try:
        from django.db import models  # noqa: F401
        is_contact_model = ModelCls.__name__.lower() == "contact"
        acting_user = getattr(request, "user", None)
        privileged = bool(
            acting_user
            and getattr(acting_user, "is_authenticated", False)
            and (
                getattr(acting_user, "is_superuser", False)
                or getattr(acting_user, "is_staff", False)
                or str(getattr(acting_user, "role", "")).lower() == "admin"
            )
        )
        if is_contact_model and not privileged:
            for forbidden in ("role", "is_staff", "is_superuser", "groups", "user_permissions"):
                clean.pop(forbidden, None)
    except Exception:
        # Defensive: do not block save on permission guard failure
        pass

    # Log and attempt tolerant mapping when nothing matched (helps with casing/formatting mismatches)
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("wcapi.save_item: incoming payload keys=%s filtered=%s", list((data or {}).keys()), list(clean.keys()))
    except Exception:
        logger = None

    if not clean and isinstance(data, dict):
        # Build a normalization helper to match keys like 'Email' -> 'email', 'email_address' -> 'emailaddress'
        def _normalize_key(s: str) -> str:
            return ''.join(ch.lower() for ch in str(s) if ch.isalnum())
        fields = {f.name for f in getattr(ModelCls._meta, "fields", [])}
        norm_map = {_normalize_key(f): f for f in fields}
        tolerant: dict = {}
        for k, v in data.items():
            nk = _normalize_key(k)
            if nk in norm_map:
                tolerant[norm_map[nk]] = v
        if tolerant:
            clean = tolerant
            try:
                if logger:
                    logger.info("wcapi.save_item: applied tolerant mapping for %s -> %s", model_key, list(clean.keys()))
            except Exception:
                pass

    if id is not None:
        obj = qs.filter(pk=id).first()
        if obj is None:
            raise LookupError("not found")
        for k, v in clean.items():
            setattr(obj, k, v)
        obj.save()
        # For updates we do not currently attempt auto-linking; return linked=False
        return obj.pk, "updated", False

    # Create the object
    obj = ModelCls.objects.create(**clean)

    # Track whether we successfully linked this creation to a contact
    linked = False

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
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("wcapi.save_item: created %s id=%s, raw_data_keys=%s, contact_id=%s, auth_user_id=%s",
                             model_key, getattr(obj, "pk", None), list(data.keys()) if isinstance(data, dict) else None, contact_id, getattr(user, "pk", None) or getattr(user, "id", None))
            except Exception:
                logger = None

            if not contact_id and user and getattr(user, "is_authenticated", False):
                # If the authenticated user is a Contact instance (AUTH_USER_MODEL='core.Contact'), use it.
                try:
                    if isinstance(user, Contact):
                        contact = user
                    else:
                        # Try to resolve a Contact record matching the auth user's pk (in case of proxy or linkage)
                        possible = Contact.objects.filter(pk=getattr(user, "pk", None)).first()
                        if possible:
                            contact = possible
                except Exception:
                    # Defensive: if contact resolution fails, continue without contact
                    contact = None

            if contact_id:
                contact = Contact.objects.filter(pk=contact_id).first()

            # Log when no contact was found so it is easier to debug client reports
            try:
                if logger and not contact and model_key and model_key.lower() in comm_models:
                    logger.info("wcapi.save_item: no contact resolved for created %s id=%s (payload_contact_id=%s, auth_user=%s)", model_key, getattr(obj, "pk", None), contact_id, getattr(user, "pk", None) or getattr(user, "id", None))
            except Exception:
                pass

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
                    linked = True

                links[bucket] = bucket_list
                refs["links"] = links
                contact.refs = refs
                # Persist contact refs with minimal update fields
                contact.save()                

                # Also ensure the created object's refs.links.contact contains the contact id
                try:
                    if not isinstance(getattr(obj, "refs", None), dict):
                        obj.refs = {}
                    obj_links = obj.refs.setdefault("links", {})
                    contact_list = obj_links.setdefault("contact", [])
                    if contact.pk not in contact_list:
                        contact_list.append(contact.pk)
                        obj.save(update_fields=["refs"])
                        linked = True
                except Exception:
                    pass

                # Also ensure a lightweight bidirectional link entry exists for quick lookup
                try:
                    if ensure_bidirectional(contact, obj, kind="contact"):
                        linked = True
                except Exception:
                    # Non-fatal if link helper fails
                    pass
    except Exception:
        # Defensive: do not block creation on linking errors
        pass

    return obj.pk, "created", linked

def delete_item(model_key: str, *, request, id: Any) -> bool:
    ModelCls, qs = get_queryset(model_key, request=request)
    obj = qs.filter(pk=id).first()
    if not obj:
        return False
    obj.delete()
    return True