"""A communication record that changes refreshes its contact's cache (Bill, 2026-10-16).

Email, Phone, Address and Domain are edited only in their own records; the contact
keeps pointers and a cache in refs.links (Contact.rebuild_communication_cache). Before
this, the cache was rebuilt only when the contact saved, so editing a phone in its card
left the contact showing the old number. The change now saves the contact itself.

A record moved from one contact to another refreshes both.

The contact's primary Email is also its login (contacts.email, unique): staff enter it in
the email card before the customer has ever signed in. The login follows that record. An
address another contact already has is refused before the save, naming that contact.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save


#: Contacts mid-save in this thread. Their own sync makes and claims Email records; those
#: saves rebuild the cache only, so a contact save never saves the contact again.
_saving = threading.local()


@contextmanager
def contact_saving(contact_id):
    ids = getattr(_saving, 'ids', None)
    if ids is None:
        ids = _saving.ids = set()
    ids.add(contact_id)
    try:
        yield
    finally:
        ids.discard(contact_id)


def _refresh(contact_id, *, login: bool = False) -> None:
    """Save the contact after one of its communication records changed.

    Bill, 2026-10-16: saving a phone, address, domain or email saves its contact too — a
    real save (version, dt_modified), so every reader of the contact sees the change, and
    the form shows it. When the record is an Email, the login moves first, so the
    contact's own sync finds the edited record instead of recreating the old address.
    """
    if not contact_id:
        return
    from apps.core.models import Contact
    contact = Contact.objects.filter(pk=contact_id).first()
    if contact is None:
        return
    if contact_id in (getattr(_saving, 'ids', None) or ()):
        contact.rebuild_communication_cache()
        return
    fields = ['dt_modified']
    if login:
        contact.rebuild_communication_cache()        # a first Email becomes the primary
        address = (contact.primary_communication('email').get('email') or None)
        if (address or '').lower() != (contact.email or '').lower():
            contact.email = address
            fields.append('email')
    contact.save(update_fields=fields)               # Contact.save rebuilds the cache


def _remember_contact(sender, instance, **kwargs):
    instance._cache_old_contact_id = (
        sender.objects.filter(pk=instance.pk).values_list('contact_id', flat=True).first()
        if instance.pk else None)


def _guard_login(sender, instance, **kwargs):
    """An email another contact already has is refused, naming that contact.

    Bill, 2026-10-16: staff who enter an address already in the database see that contact
    open beside their entry and decide — abandon theirs, or update the existing record.
    The refusal carries the contact's id for that (error.details.contact_id). Unowned Email
    records are not owners; admins assign those from the unassigned-email list.
    """
    from django.db.models import Q
    from apps.core.models import Contact
    from apps.core.services.door import Refused
    instance.email = (instance.email or '').strip()
    if not instance.contact_id or not instance.email:
        return
    other = (Contact.objects.filter(Q(email__iexact=instance.email)
                                    | Q(emails__email__iexact=instance.email))
             .exclude(pk=instance.contact_id).values_list('id', flat=True).first())
    if other:
        raise Refused(409, 'email_in_use',
                      f'{instance.email} already belongs to contact #{other}. It is open in '
                      f'another window: abandon this entry, or update that contact.',
                      {'field': 'email', 'email': instance.email, 'contact_id': other})


def _is_login(contact_id, email_pk) -> bool:
    from apps.core.models import Contact
    return Contact.objects.filter(pk=contact_id).filter(
        Q(email_id=email_pk) | Q(email_id__isnull=True)).exists()


def _after_save(sender, instance, **kwargs):
    email = sender.__name__ == 'Email'
    old = getattr(instance, '_cache_old_contact_id', None)
    _refresh(instance.contact_id,
             login=email and bool(instance.contact_id) and _is_login(instance.contact_id, instance.pk))
    if old and old != instance.contact_id:
        _refresh(old, login=email)


def _remember_login(sender, instance, **kwargs):
    instance._was_login = bool(instance.contact_id) and _is_login(instance.contact_id, instance.pk)


def _after_delete(sender, instance, **kwargs):
    _refresh(instance.contact_id, login=getattr(instance, '_was_login', False))


def register_communication_signals() -> None:
    from apps.communications.models import Address, Domain, Email, Phone
    for model in (Email, Phone, Address, Domain):
        uid = f'comm-cache-{model.__name__}'
        pre_save.connect(_remember_contact, sender=model, dispatch_uid=f'{uid}-pre')
        if model is Email:
            pre_save.connect(_guard_login, sender=model, dispatch_uid=f'{uid}-login')
            pre_delete.connect(_remember_login, sender=model, dispatch_uid=f'{uid}-was-login')
        post_save.connect(_after_save, sender=model, dispatch_uid=f'{uid}-post')
        post_delete.connect(_after_delete, sender=model, dispatch_uid=f'{uid}-delete')
