"""A communication record that changes refreshes its contact's cache (Bill, 2026-10-16).

Email, Phone, Address and Domain are edited only in their own records; the contact
keeps pointers and a cache in refs.links (Contact.rebuild_communication_cache). Before
this, the cache was rebuilt only when the contact saved, so editing a phone in its card
left the contact showing the old number.

A record moved from one contact to another refreshes both.
"""
from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save


def _rebuild(contact_id) -> None:
    if not contact_id:
        return
    from apps.core.models import Contact
    contact = Contact.objects.filter(pk=contact_id).first()
    if contact is not None:
        contact.rebuild_communication_cache()


def _remember_contact(sender, instance, **kwargs):
    instance._cache_old_contact_id = (
        sender.objects.filter(pk=instance.pk).values_list('contact_id', flat=True).first()
        if instance.pk else None)


def _after_save(sender, instance, **kwargs):
    old = getattr(instance, '_cache_old_contact_id', None)
    _rebuild(instance.contact_id)
    if old and old != instance.contact_id:
        _rebuild(old)


def _after_delete(sender, instance, **kwargs):
    _rebuild(instance.contact_id)


def register_communication_signals() -> None:
    from apps.communications.models import Address, Domain, Email, Phone
    for model in (Email, Phone, Address, Domain):
        uid = f'comm-cache-{model.__name__}'
        pre_save.connect(_remember_contact, sender=model, dispatch_uid=f'{uid}-pre')
        post_save.connect(_after_save, sender=model, dispatch_uid=f'{uid}-post')
        post_delete.connect(_after_delete, sender=model, dispatch_uid=f'{uid}-delete')
