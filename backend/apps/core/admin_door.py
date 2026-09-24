"""Django admin goes through the save door like everything else.

Bill, 2026-09-22: *"I think everything should flow through this one door including Django
admin. No staff backdoor."*

Django's ``ModelAdmin.save_model`` calls ``obj.save()`` directly, so an admin edit has
always skipped what the REST save (``POST /wcapi/<model>/``) applies: the field policy, envelope validation, the
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
from apps.core.services.delete import delete_record
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

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


    def delete_model(self, request, obj):  # noqa: D102 - Django's contract
        """A delete from admin meets the same guards as one from wcapi: the hard-delete
        rule, the cash door, the model's own delete()."""
        actor = Actor(user=getattr(request, 'user', None), kind='staff', source='admin')
        model_key = to_model_name(type(obj)) or type(obj)._meta.model_name
        try:
            delete_record(actor, model_key, obj.pk, visible_only=False)
        except Refused as refused:
            logger.info("[ADMIN] Delete refused (%s): %s", refused.code, refused.message)
            raise ValidationError(refused.message) from refused

    def delete_queryset(self, request, queryset):  # noqa: D102 - Django's contract
        """The bulk action, one record at a time, so each meets its own guards. A refusal
        stops the batch and says which record refused."""
        for obj in queryset:
            self.delete_model(request, obj)


def _on_door(cls):
    """The ModelAdmin class, with the door in front of it."""
    if issubclass(cls, WcAdminMixin):
        return cls
    return type(f'Door{cls.__name__}', (WcAdminMixin, cls), {})


def install() -> None:
    """Put admin on the door — the ones registered already, and every later one.

    Timing is the whole problem: Django registers admin classes when it autodiscovers
    ``admin.py`` modules, which may happen before or after this app is ready depending on
    ``INSTALLED_APPS`` order. So rather than walk the registry once and hope, this wraps
    ``AdminSite.register`` itself. A ModelAdmin written next year, in an app added next
    year, is on the door because there is no way to register one that is not.
    """
    # admin.site is a lazy proxy (DefaultAdminSite); the class to patch is AdminSite
    # itself, which every site — the default one and any custom one — is built from.
    site_cls = admin.AdminSite
    if not getattr(site_cls, '_wc_door_installed', False):
        original_register = site_cls.register

        def register(self, model_or_iterable, admin_class=None, **options):
            if admin_class is not None:
                admin_class = _on_door(admin_class)
            elif options:
                # Django builds a ModelAdmin from the options; wrap that.
                options['__module__'] = __name__
                admin_class = _on_door(type('ModelAdmin', (admin.ModelAdmin,), options))
                options = {}
            else:
                admin_class = _on_door(admin.ModelAdmin)
            return original_register(self, model_or_iterable, admin_class, **options)

        site_cls.register = register
        site_cls._wc_door_installed = True

    # Anything registered before this ran.
    rewrapped = 0
    for model, model_admin in list(admin.site._registry.items()):
        cls = type(model_admin)
        if issubclass(cls, WcAdminMixin):
            continue
        admin.site._registry[model] = _on_door(cls)(model, admin.site)
        rewrapped += 1
    logger.info("[ADMIN] save/delete doors installed; %s existing admin classes rewrapped",
                rewrapped)
