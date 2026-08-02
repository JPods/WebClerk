"""
core.services.wcui_prefs — Save UI preferences to Contact.metadata.wcui

Preferences belong on the user's Contact record, not in the browser.
localStorage is the cache; the Contact record is the source of truth.

Called via wcapi/manage { action: "save_wcui_prefs", prefs: { font_size: 16 } }
"""
import logging
from django.apps import apps

log = logging.getLogger(__name__)


def save_wcui_prefs(prefs: dict, contact_id: int = None) -> dict:
    """
    Merge prefs into Contact.metadata.wcui for the current user.

    If contact_id is not provided, uses the request context (TODO: wire auth).
    For now, accepts contact_id explicitly or defaults to id=8 (Bill).
    """
    if not prefs:
        return {"saved": False, "reason": "no prefs provided"}

    Contact = apps.get_model('core', 'Contact')

    # TODO: get contact_id from request.user when auth is wired
    cid = contact_id or 8  # fallback to Bill's ID for now

    try:
        contact = Contact.objects.get(id=cid)
    except Contact.DoesNotExist:
        return {"saved": False, "reason": f"contact {cid} not found"}

    metadata = contact.metadata if isinstance(contact.metadata, dict) else {}
    wcui = metadata.get('wcui', {})
    wcui.update(prefs)
    metadata['wcui'] = wcui
    contact.metadata = metadata
    contact.save(update_fields=['metadata', 'dt_modified'])

    log.info(f"Saved wcui prefs for contact {cid}: {list(prefs.keys())}")
    return {"saved": True, "contact_id": cid, "keys": list(prefs.keys())}
