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

def save_item(model_key: str, *, request, data: Dict[str, Any], id: Any = None) -> Tuple[Any, str, bool]:
    ModelCls, qs = get_queryset(model_key, request=request)
    clean = filter_input_fields(ModelCls, data)

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