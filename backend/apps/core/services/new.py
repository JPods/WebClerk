"""The `new` verb — the backend makes a record and hands it to the front end.

Bill, 2026-09-26: "The creation of a record should be a backend behavior that hands the
front a new record … It is very important to properly populate a new record." The front
end never builds a record: ``POST /wcapi/<model>/`` saves an empty one and returns it with
its id. The values come afterwards, as a save (``PUT /wcapi/<model>/<id>/``).

    Setting defaults → config.is_new → save_record (its hooks populate) → the record

- **Defaults** are the model's ``Setting(purpose='wc:model').prefs.defaults``, which users
  edit. ``<field>_offset_days: N`` is that many days from now (UTC epoch ms). They pass the
  role's field filter like any value, so a default only reaches a field the role may edit;
  a rule that needs logic (rep = the actor, a status, a copy from a parent) is the model's
  code hook.
- **The mark** ``config.is_new`` is set before the hooks (``save._mark_new``), so the code
  hook and the user's ``<model>.save_pre`` Report case on ``if config.is_new``. The next
  save removes it; Alice sweeps records that keep it.
- **No values.** A body carrying fields is refused with coaching; the underscore signals a
  model's behaviour declares (``_parent``) pass, for its hook to read.

Plan: Allie ``readmes/assessments/2026-09-26-new-verb.md``.
"""
from __future__ import annotations

import time
from typing import Any, Dict

from apps.core.services.door import Actor, Refused

#: Payload keys the channel adds that are not values: the path's model, and no id.
_ENVELOPE = frozenset({'model_name', 'id'})
_DAY_MS = 86_400_000


def new_record(actor: Actor, model_key: str, payload: dict):
    from django.core.exceptions import ObjectDoesNotExist
    from django.db import IntegrityError

    from apps.core.services.behaviours import behaviour_for
    from apps.core.services.save import resolve_model, save_record

    _model_cls, model_key, _norm = resolve_model(model_key)
    if payload.get('id') is not None:
        raise Refused(400, 'id_in_new',
                      f'new makes a record; to change {model_key} {payload["id"]}, '
                      f'PUT /wcapi/{model_key}/{payload["id"]}/.',
                      {'id': payload['id']})
    requires = tuple(behaviour_for(model_key).NEW_REQUIRES)
    values = sorted(k for k in payload
                    if k not in _ENVELOPE and not k.startswith('_') and k not in requires)
    if values:
        also = f' It takes only {", ".join(requires)}.' if requires else ''
        raise Refused(400, 'new_takes_no_values',
                      f'new saves an empty {model_key} and returns it with its id; PUT the '
                      f'values to /wcapi/{model_key}/<id>/.{also} Sent: {", ".join(values)}.',
                      values)
    missing = [k for k in requires if payload.get(k) in (None, '')]
    if missing:
        raise Refused(400, 'new_requires',
                      f'A {model_key} cannot exist without {", ".join(missing)}; send '
                      f'{"them" if len(missing) > 1 else "it"} to new.', missing)

    data = setting_defaults(model_key)
    data.update({k: v for k, v in payload.items() if k.startswith('_') or k in requires})
    data['model_name'] = model_key
    try:
        return save_record(actor, data, model_key=model_key, new=True)
    except (IntegrityError, ObjectDoesNotExist) as e:
        # A model that cannot be saved empty and declares nothing: coached, never a 500.
        # The fix is its behaviour's NEW_REQUIRES, or its is_new case populating it.
        detail = str(e).splitlines()[0][:200]
        raise Refused(400, 'new_incomplete',
                      f'A {model_key} cannot be saved empty ({detail}). Its behaviour must '
                      f'declare NEW_REQUIRES or populate it when config.is_new.',
                      {'model_name': model_key, 'detail': detail})


def setting_defaults(model_key: str) -> Dict[str, Any]:
    """The model's ``prefs.defaults``, with ``<field>_offset_days`` turned into dates."""
    from apps.core.models import Setting
    setting = (Setting.objects.filter(purpose='wc:model', parent_model=model_key)
               .only('prefs').first())
    defaults = ((setting.prefs or {}).get('defaults') if setting else None) or {}
    now_ms = int(time.time() * 1000)
    out: Dict[str, Any] = {}
    for key, value in defaults.items():
        if value == '' or value is None:
            continue
        if key.endswith('_offset_days'):
            out[key[:-len('_offset_days')]] = now_ms + int(float(value) * _DAY_MS)
        else:
            out[key] = value
    return out


def clear_mark(obj) -> None:
    """The record is no longer new: the next save (``save._mark_new``), or for a card Cash
    the gateway's reply (``cash_commands.record_outcome``)."""
    config = getattr(obj, 'config', None)
    if isinstance(config, dict) and 'is_new' in config:
        obj.config = {k: v for k, v in config.items() if k != 'is_new'}
        # For the model's own save(): this save fills a record `new` saved empty, so what a
        # model seeds on its first insert (a Cash's available, tendered) is seeded now.
        obj._filling_new = True
