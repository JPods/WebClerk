from __future__ import annotations
import json
import logging
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple
from django.forms.models import model_to_dict
from django.db.models import Model, QuerySet
from apps.core.utils import registry, policy

logger = logging.getLogger(__name__)


def _log_save_action(
    request: Any,
    model_name: str,
    record_id: int,
    action: str,
    old_values: Optional[Dict[str, Any]],
    new_values: Dict[str, Any],
) -> None:
    """Log a save action to the audit log.
    
    Uses a savepoint to ensure audit logging failures don't poison the transaction.
    """
    from django.db import connection
    
    # Use a savepoint so audit logging failures don't poison any active transaction
    sid = connection.savepoint()
    try:
        from apps.core.models.audit import AuditLog
        
        changes = {'new': new_values}
        if old_values:
            changes['old'] = old_values
        
        AuditLog.log_action(
            request=request,
            model_name=model_name,
            id_record=record_id,
            action=action,
            changes=changes,
            metadata={},
        )
        connection.savepoint_commit(sid)
    except Exception as e:
        # Roll back the savepoint so any active transaction can continue
        connection.savepoint_rollback(sid)
        # Don't fail the save if audit logging fails
        logger.warning(
            "Failed to create audit log: model=%s id=%s action=%s error=%s",
            model_name, record_id, action, str(e)
        )


def to_dict(obj: Model, *, allow: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    data = model_to_dict(obj)
    filtered = {k: data.get(k) for k in allow} if allow else data

    field_map = {}
    try:
        field_map = {f.name: f for f in obj._meta.get_fields() if getattr(f, "name", None)}
    except Exception:
        field_map = {}

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
        # Note: removed refresh_from_db() as it clears prefetch_related cache
        # The get() query already fetches fresh data from the database
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
        # Capture old values for audit logging
        old_values = {k: getattr(obj, k, None) for k in clean.keys()}
        for k, v in clean.items():
            setattr(obj, k, v)
        obj.save()
        # Log the update to audit trail
        _log_save_action(request, model_key, obj.pk, 'updated', old_values, clean)
        # For updates we do not currently attempt auto-linking; return linked=False
        return obj.pk, "updated", False

    # Create the object
    obj = ModelCls.objects.create(**clean)
    # Log the creation to audit trail
    _log_save_action(request, model_key, obj.pk, 'created', None, clean)

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
                logger.debug("wcapi.save_item: created %s id=%s requested by user id=%s auth=%s payload_contact_id=%s",
                             model_key, getattr(obj, "pk", None), getattr(user, "pk", None) or getattr(user, "id", None), getattr(user, "is_authenticated", None), contact_id)
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
    # Log the deletion to audit trail before actually deleting
    _log_save_action(request, model_key, id, 'deleted', None, {})
    obj.delete()
    return True