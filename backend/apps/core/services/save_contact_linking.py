"""Contact linking service for the universal save pipeline.

Handles bidirectional refs linking between communication records
(email, phone, address, domain) and their Contact. Consolidates
the duplicate linking logic that was in save_view.py.

Part of the save_* service cluster:
  save_field_assignment.py   — field coercion, JSON merge
  save_line_processing.py    — line CRUD for header models
  save_envelope.py           — Pydantic envelope validation
  save_contact_linking.py    — this file
"""
from __future__ import annotations

import logging
from django.db import models
from django.utils import timezone

console_logger = logging.getLogger('console')


def link_obj_to_contact(obj, contact) -> bool:
    """Add contact.pk to obj.refs.links.contact[] if not already present.

    Returns True if obj was modified (caller should save).
    """
    if not contact or not getattr(contact, 'pk', None):
        return False

    refs = getattr(obj, 'refs', None)
    if not isinstance(refs, dict):
        refs = {}
        obj.refs = refs

    obj_links = refs.setdefault('links', {})
    contact_list = obj_links.setdefault('contact', [])

    if contact.pk not in contact_list:
        contact_list.append(contact.pk)
        return True
    return False


def link_comm_to_contact(obj, contact, bucket: str, denorm_fields: list[str]) -> bool:
    """Link a communication record to a contact via refs.links.

    Updates contact.refs.links.<bucket> with denormalized fields from obj.
    Updates obj.refs.links.contact with contact.pk.
    Calls ensure_bidirectional.

    Returns True if linking occurred.
    """
    if not contact or not bucket:
        return False

    from apps.core.models import Contact
    from common.refs.links import ensure_bidirectional

    # Build denormalized entry for the comm record
    denorm = {f: getattr(obj, f, None) for f in denorm_fields}

    # Update contact.refs.links.<bucket>
    refs = getattr(contact, 'refs', {}) or {}
    links = refs.get('links') or {}
    bucket_list = links.get(bucket) or []

    existing_found = False
    for idx, it in enumerate(list(bucket_list)):
        if isinstance(it, dict) and it.get('id') == getattr(obj, 'pk'):
            bucket_list[idx] = denorm
            existing_found = True
            break
        if isinstance(it, int) and it == getattr(obj, 'pk'):
            bucket_list[idx] = denorm
            existing_found = True
            break

    if not existing_found:
        bucket_list.append(denorm)

    links[bucket] = bucket_list
    refs['links'] = links
    contact.refs = refs

    # Save contact via .update() for atomicity
    Contact.objects.filter(pk=contact.pk).update(
        refs=contact.refs,
        version=models.F('version') + 1,
        dt_modified=int(timezone.now().timestamp() * 1000),
    )

    # Update obj.refs.links.contact
    modified = link_obj_to_contact(obj, contact)
    if modified:
        obj.save()

    # Bidirectional
    try:
        ensure_bidirectional(contact, obj, kind='contact')
    except Exception:
        pass

    return True
