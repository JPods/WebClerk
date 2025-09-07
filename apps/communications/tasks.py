# path: apps/communications/tasks.py
from celery import shared_task
from typing import Any, Dict

from django.apps import apps

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
def validate_location_osm(location_id: int) -> Dict[str, Any]:
    """Stub address verification using an OSM-like provider.

    No external call is made; we record a 'stubbed' status. Replace later with
    an actual Nominatim request and mapping. The model's apply_validation_result
    will map fields and update metadata.
    """
    Location = apps.get_model('communications', 'Location')
    loc = Location.objects.filter(pk=location_id).first()
    if not loc:
        return {"ok": False, "error": "not_found"}
    result = {
        "provider": "osm",
        "status": "stubbed",
        "match_score": 0,
        # Optionally include lat/long and normalized fields when real API added
    }
    try:
        loc.apply_validation_result(result)
        return {"ok": True, "applied": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@shared_task
def validate_email_format(email_id: int) -> Dict[str, Any]:
    """Stub email validation. Replace with SMTP or third-party verifier later."""
    Email = apps.get_model('communications', 'Email')
    obj = Email.objects.filter(pk=email_id).first()
    if not obj:
        return {"ok": False, "error": "not_found"}
    # Could set metadata.versioning.validation = { provider:'local', status:'checked' }
    meta = obj.metadata or {}
    ver = meta.setdefault('versioning', {}).setdefault('validation', {})
    ver.update({"provider": "local", "status": "stubbed"})
    obj.metadata = meta
    obj.save(update_fields=['metadata', 'dt_modified', 'version'])
    return {"ok": True}


@shared_task
def validate_phone_basic(phone_id: int) -> Dict[str, Any]:
    """Stub phone validation. Could add E.164 normalization later."""
    Phone = apps.get_model('communications', 'Phone')
    obj = Phone.objects.filter(pk=phone_id).first()
    if not obj:
        return {"ok": False, "error": "not_found"}
    meta = obj.metadata or {}
    ver = meta.setdefault('versioning', {}).setdefault('validation', {})
    ver.update({"provider": "local", "status": "stubbed"})
    obj.metadata = meta
    obj.save(update_fields=['metadata', 'dt_modified', 'version'])
    return {"ok": True}