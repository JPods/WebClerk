"""Guard Settings on save.

Any Setting is refused when its config holds a credential: a non-empty value
under a key named like password, secret, api_key, signing_key, private_key or
token. Settings are read by every login; credentials belong on Connection
records (Bill, 2026-09-18).

A Setting(purpose='wc:model') is also refused when its config.access.roles
names a wildcard, a parent path, a path that is not a leaf, an unknown role, or
an edit leaf that is not viewable. The access cache is cleared on every save.
"""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError

CREDENTIAL_KEY = re.compile(r'(^|_)(password|secret|api_?key|signing_key|private_key|(access_|gateway_)?token)$',
                            re.IGNORECASE)


def credential_paths(value, path: str = 'config') -> list[str]:
    """Paths in a Setting config that hold a non-empty value under a credential-named key."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = f'{path}.{key}'
            if CREDENTIAL_KEY.search(str(key)) and not isinstance(child, (dict, list)) and str(child or '').strip():
                found.append(here)
            found += credential_paths(child, here)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found += credential_paths(child, f'{path}[{i}]')
    return found
from django.db.models.signals import post_delete, post_save, pre_save


def _guard(sender, instance, **kwargs):
    secrets = credential_paths(instance.config or {})
    if secrets:
        raise ValidationError({'config': [
            f'{p}: credentials belong in a Connection record — every login can read Settings'
            for p in secrets[:20]]})
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
