"""Django admin goes through the save door like everything else.

Bill, 2026-09-22: *"I think everything should flow through this one door including Django
admin. No staff backdoor."*

Django's ``ModelAdmin.save_model`` calls ``obj.save()`` directly, so an admin edit has
always skipped what ``/wcapi/save/`` applies: the field policy, envelope validation, the
model's own behaviour, the report hooks, the version check and the sync push. It got the
base model's identity work and nothing else.

``WcAdminMixin`` puts admin on the same path. It is a mixin rather than a per-model
override so a ``ModelAdmin`` written later cannot opt out by being written without it:
``admin_door.install()`` applies it to every registered admin at startup.

The actor is ``staff``: a real person, with the admin as the source, recorded that way.
"""
from __future__ import annotations

import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models as dj_models

from apps.core.constants.model_registry import to_model_name
from apps.core.services.save import Actor, Refused, save_record

logger = logging.getLogger(__name__)


def _payload_from_form(obj, form, change: bool) -> dict:
    """The door takes a payload, not a populated instance.

    Admin gives a bound form: ``cleaned_data`` is what the person actually submitted,
    already coerced by Django. Related objects become their ids, because that is what the
    door's field assignment expects.
    """
    data = {'model_name': to_model_name(type(obj)) or type(obj)._meta.model_name}
    if change and obj.pk:
        data['id'] = obj.pk
        version = getattr(obj, 'version', None)
        if version is not None:
            data['version'] = version

    for name, value in (getattr(form, 'cleaned_data', None) or {}).items():
        try:
            field = type(obj)._meta.get_field(name)
        except Exception:  # noqa: BLE001 — a form field with no model field behind it
            data[name] = value
            continue
        if isinstance(field, dj_models.ManyToManyField):
            data[name] = [getattr(v, 'pk', v) for v in (value or [])]
        elif field.is_relation:
            data[f'{name}_id'] = getattr(value, 'pk', value)
        else:
            data[name] = value
    return data


class WcAdminMixin:
    """Routes an admin save through the one door."""

    def save_model(self, request, obj, form, change):  # noqa: D102 - Django's contract
        actor = Actor(user=getattr(request, 'user', None), kind='staff', source='admin')
        try:
            result = save_record(actor, _payload_from_form(obj, form, change))
        except Refused as refused:
            # Admin speaks in form errors, so a refusal is raised as one: the person sees
            # why on the page they are on, rather than a 500.
            logger.info("[ADMIN] Save refused (%s): %s", refused.code, refused.message)
            raise ValidationError(refused.message) from refused

        # Admin holds its own instance; give it the door's, so the change message and the
        # response reflect what was actually written.
        obj.pk = result.obj_id
        obj.refresh_from_db()
        for note in result.messages:
            messages.warning(request, note)
        if result.warning:
            messages.warning(request, result.warning)


def install() -> None:
    """Put every registered ModelAdmin on the door. Called from AppConfig.ready()."""
    installed = 0
    for model, model_admin in list(admin.site._registry.items()):
        cls = type(model_admin)
        if issubclass(cls, WcAdminMixin):
            continue
        patched = type(f'Door{cls.__name__}', (WcAdminMixin, cls), {})
        admin.site._registry[model] = patched(model, admin.site)
        installed += 1
    logger.info("[ADMIN] %s admin classes routed through the save door", installed)
