"""Guard the access lists in wc:model Settings.

A Setting(purpose='wc:model') is refused on save when its config.access.roles
names a wildcard, a parent path, a path that is not a leaf, an unknown role, or
an edit leaf that is not viewable. The access cache is cleared on every save.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete, post_save, pre_save


def _guard(sender, instance, **kwargs):
    if instance.purpose != 'wc:model':
        return
    acc = (instance.config or {}).get('access') or {}
    if not acc.get('roles'):
        return
    from apps.core.services.access import validate_access
    problems = validate_access(instance.parent_model, acc)
    if problems:
        raise ValidationError({'config.access.roles': problems[:20]})


def _clear(sender, instance, **kwargs):
    if instance.purpose == 'wc:model':
        from apps.core.services.access import clear_cache
        clear_cache(instance.parent_model)


def register_access_signals():
    from apps.core.models.setting import Setting
    pre_save.connect(_guard, sender=Setting, dispatch_uid='access_guard')
    post_save.connect(_clear, sender=Setting, dispatch_uid='access_clear_save')
    post_delete.connect(_clear, sender=Setting, dispatch_uid='access_clear_delete')
