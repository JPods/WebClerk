# path: apps/communications/tasks.py
from celery import shared_task
from typing import Any, Dict, cast

from django.apps import apps
from apps.sync.services.email_verification import verify_email_via_connection
from apps.sync.services.phone_verification import verify_phone_via_connection
from apps.sync.services.location_verification import verify_location_via_connection
from apps.sync.services.domain_verification import verify_domain_via_connection

@shared_task
def hello():
    # Example: check roles, permissions, or custom logic
    return {'success': False, 'message': 'Only superusers can assign admin role.'}

@shared_task
def save_pre_contact(data):
    # Implement your logic to save pre-contact data
    return {'success': True, 'message': 'Pre-contact data saved successfully.'}

@shared_task
def save_post_contact(data):
    # Implement your logic to save post-contact data
    return {'success': True, 'message': 'Post-contact data saved successfully.'}    

def user_id_is_superuser(user_id):
    # Implement your logic here
    return True


# -------- Validation / cleanup stubs ---------------------------------------
@shared_task
def validate_location_osm(location_id: int, connection_name: str | None = None) -> Dict[str, Any]:
    """Location verification via Connection/Exchange (stubbed provider).

    Builds a minimal location payload and verifies through a Connection of
    type 'location_verification'. Records review pending exchange in metadata.
    """
    Location = apps.get_model('communications', 'Location')
    loc = Location.objects.filter(pk=location_id).first()
    if not loc:
        return {"ok": False, "error": "not_found"}
    payload = {
        "address1": getattr(loc, "address1", ""),
        "address2": getattr(loc, "address2", ""),
        "city": getattr(loc, "city", ""),
        "state": getattr(loc, "state", ""),
        "zip": getattr(loc, "zip", ""),
        "country": getattr(loc, "country", ""),
    }
    res = verify_location_via_connection(payload, connection_name)
    result = res.get("result") or {}
    exchange_id = res.get("exchange_id")

    try:
        obj = cast(Any, loc)
        if hasattr(obj, "apply_validation_result"):
            obj.apply_validation_result(result)
        # Ensure review info is present
        meta = getattr(obj, "metadata", {}) or {}
        ver = meta.setdefault("versioning", {}).setdefault("validation", {})
        rev = ver.setdefault("review", {})
        rev.update({"status": "pending", "exchange_id": exchange_id})
        obj.metadata = meta
        obj.save(update_fields=["metadata", "dt_modified", "version"])  # type: ignore[attr-defined]
        return {"ok": True, "applied": True, "exchange_id": exchange_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@shared_task
def validate_email_format(email_id: int) -> Dict[str, Any]:
    """Stub email validation. Replace with SMTP or third-party verifier later."""
    Email = apps.get_model('communications', 'Email')
    obj = Email.objects.filter(pk=email_id).first()
    if not obj:
        return {"ok": False, "error": "not_found"}
    # Use provider-agnostic verification via sync Connection/Exchange.
    email_addr = getattr(obj, "email", "")
    res = verify_email_via_connection(email_addr)
    meta = getattr(obj, "metadata", {}) or {}
    ver = meta.setdefault('versioning', {}).setdefault('validation', {})
    result = res.get('result') or {}
    ver.update({
        "provider": result.get('provider', 'stub'),
        "status": result.get('status', 'stubbed'),
        "deliverability": result.get('deliverability', 'unknown'),
        "reason": result.get('reason', ''),
        "review": {"status": "pending", "exchange_id": res.get('exchange_id')},
    })
    obj.metadata = meta  # type: ignore[attr-defined]
    # Defer flipping is_verified until review acceptance.
    obj.save(update_fields=['metadata', 'dt_modified', 'version'])  # type: ignore[attr-defined]
    return {"ok": True, "result": result}


@shared_task
def validate_phone_basic(phone_id: int) -> Dict[str, Any]:
    """Phone verification via Connection/Exchange (stubbed).

    Records review-pending exchange_id in metadata.
    """
    Phone = apps.get_model('communications', 'Phone')
    obj = Phone.objects.filter(pk=phone_id).first()
    if not obj:
        return {"ok": False, "error": "not_found"}
    number = getattr(obj, "number", "")
    res = verify_phone_via_connection(number)
    result = res.get("result") or {}
    exchange_id = res.get("exchange_id")

    meta = getattr(obj, "metadata", {}) or {}
    ver = meta.setdefault('versioning', {}).setdefault('validation', {})
    ver.update({
        "provider": result.get('provider', 'stub'),
        "status": result.get('status', 'stubbed'),
        "valid": result.get('valid', None),
        "reason": result.get('reason', ''),
        "review": {"status": "pending", "exchange_id": exchange_id},
    })
    obj.metadata = meta  # type: ignore[attr-defined]
    obj.save(update_fields=['metadata', 'dt_modified', 'version'])  # type: ignore[attr-defined]
    return {"ok": True, "result": result}


@shared_task
def validate_domain_basic(domain_id: int) -> Dict[str, Any]:
    """Domain verification via Connection/Exchange (stubbed)."""
    Domain = apps.get_model('communications', 'Domain')
    obj = Domain.objects.filter(pk=domain_id).first()
    if not obj:
        return {"ok": False, "error": "not_found"}
    path = getattr(obj, "path", "")
    res = verify_domain_via_connection(path)
    result = res.get("result") or {}
    exchange_id = res.get("exchange_id")

    meta = getattr(obj, "metadata", {}) or {}
    ver = meta.setdefault('versioning', {}).setdefault('validation', {})
    ver.update({
        "provider": result.get('provider', 'stub'),
        "status": result.get('status', 'stubbed'),
        "reachable": result.get('reachable', None),
        "reason": result.get('reason', ''),
        "review": {"status": "pending", "exchange_id": exchange_id},
    })
    obj.metadata = meta  # type: ignore[attr-defined]
    obj.save(update_fields=['metadata', 'dt_modified', 'version'])  # type: ignore[attr-defined]
    return {"ok": True, "result": result}