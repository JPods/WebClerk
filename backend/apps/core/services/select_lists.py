"""Select lists — each model's own, in its definition (Bill, 2026-10-28).

config.selectlists.<field> on a model's wc:model Setting lists the values that field offers:
the dropdown, and what the door expects. They support, they do not police (Bill, 2026-10-29):
a person who saves a value not on its list is asked first, and one click adds it (add_value);
code that writes a new value adds it as it saves, logged, because no one is there to ask and
operations must not stop. A login flagged is_staff may change any list (Bill, 2026-10-29). A
field with no list, and an empty value, are never checked.
"""
from __future__ import annotations

from typing import Any, Optional

from django.db import transaction


def _build(selectlists) -> dict[str, frozenset]:
    out = {}
    for field, options in (selectlists or {}).items() if isinstance(selectlists, dict) else ():
        if isinstance(options, list):
            out[field] = frozenset(str(o.get('value') if isinstance(o, dict) else o) for o in options)
    return out


def _key(name: str) -> str:
    from apps.core.services.access import model_key
    return model_key(name) or name


def lists(name: str) -> dict[str, frozenset]:
    """{field: its listed values} for model `name` (cached; definition.py)."""
    from apps.core.services import definition
    return definition.part(_key(name), ('selectlists',), _build)


def unlisted(name: str, values: dict[str, Any]) -> dict[str, Any]:
    """The {field: value} pairs of `values` that are set and not on their field's list."""
    listed = lists(name)
    return {f: v for f, v in values.items()
            if v not in (None, '') and f in listed and str(v) not in listed[f]}


def may_edit_list(actor, name: str, field: str) -> bool:
    """Lists are changed by a login flagged is_staff, or by the code (Bill, 2026-10-29)."""
    from apps.core.services.door import as_actor
    actor = as_actor(actor)
    if not actor.is_guarded:
        return True
    return bool(actor.user is not None and getattr(actor.user, 'is_staff', False))


def _write(name: str, field: str, change, actor) -> list:
    """Apply change(options) -> options to one field's list; returns the new list."""
    from apps.core.models import Setting
    from apps.core.models.log import Log
    from apps.core.services import definition
    from apps.core.services.door import Refused, as_actor
    key = _key(name)
    if actor is not None and not may_edit_list(actor, key, field):
        raise Refused(403, 'list_edit_forbidden',
                      f"Only staff change lists; ask a staff member to add to the {key} {field} "
                      f"list.", {'model_name': key, 'field': field})
    with transaction.atomic():
        model_def = (Setting.objects.select_for_update()
                     .filter(purpose='wc:model', parent_model=key).order_by('id').first())
        if model_def is None:
            raise Refused(404, 'no_definition', f'{key} has no model definition to hold a list.',
                          {'model_name': key})
        config = dict(model_def.config or {})
        selectlists = dict(config.get('selectlists') or {})
        before = list(selectlists.get(field) or [])
        after = change(before)
        if after == before:
            return after
        selectlists[field] = after
        config['selectlists'] = selectlists
        Setting.objects.filter(pk=model_def.pk).update(config=config)
        definition.clear(key)              # before the log row, which reads the log's own list
        Log.write('audit', 'list_changed', model_name='setting', record_id=model_def.pk,
                  name=f'{key}.{field}', changes={field: {'old': before, 'new': after}},
                  user=as_actor(actor).user if actor is not None and as_actor(actor).user else None)
    return after


def add_value(name: str, field: str, value, *, actor=None, label: Optional[str] = None) -> list:
    """Add one value to a field's list (no-op when it is there). actor None = the code."""
    def add(options):
        if str(value) in {str(o.get('value') if isinstance(o, dict) else o) for o in options}:
            return options
        return options + [{'value': value, 'label': label or str(value)}]
    return _write(name, field, add, actor)


def replace_list(name: str, field: str, options: list, *, actor) -> list:
    """Rename, remove or reorder: the field's list becomes `options` ([{value, label}])."""
    from apps.core.services.door import Refused
    if not isinstance(options, list) or not all(isinstance(o, dict) and 'value' in o for o in options):
        raise Refused(400, 'list_invalid', 'A list is [{"value": …, "label": …}, …].', options)
    return _write(name, field, lambda _old: [{'value': o['value'], 'label': o.get('label') or str(o['value'])}
                                             for o in options], actor)
