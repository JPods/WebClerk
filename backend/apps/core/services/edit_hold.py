"""Edit holds — one person edits a record at a time (Bill, 2026-11-02: "can we add timer into records
when they are individually called by the front end that locks them to the edit of others until the
timer runs out, or the first caller loads another record of that model?"; "15 minutes as a
setting.company...edit delay"; "a notice to the person who cannot edit").

    POST /wcapi/<model>/<id>/hold/      take or extend the hold; or learn who has it
    POST /wcapi/<model>/<id>/release/   give it back (closing the form)

A hold lives in the cache, never in the record: taking one writes nothing to the record (no
version bump, no sync traffic) and a save pays one cache read. Taking a hold on a record gives back
the person's hold on any other record of that model. It lasts the company's edit delay
(``wc:company_profile`` ``config.edit_delay_minutes``, 15 by default) and the form extends it while
the person works. Anyone else's save of a held record is refused (423) with who holds it and until
when. The version check (412) stays underneath: it covers what a hold cannot see — a desktop and a
cloud copy offline, a save that never opened a form.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from django.core.cache import cache

from apps.core.services.door import Refused

DEFAULT_MINUTES = 15


def minutes() -> int:
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile').only('config').first()
    value = ((company.config or {}) if company else {}).get('edit_delay_minutes')
    try:
        return max(1, int(value)) if value not in (None, '') else DEFAULT_MINUTES
    except (TypeError, ValueError):
        return DEFAULT_MINUTES


def _key(model_key: str, record_id) -> str:
    return f'wc:hold:{model_key}:{record_id}'


def _mine_key(contact_id, model_key: str) -> str:
    return f'wc:hold:who:{contact_id}:{model_key}'


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace('+00:00', 'Z')


def holder(model_key: str, record_id) -> Optional[dict]:
    """The live hold on a record: {contact_id, name, until (epoch ms)}, or None."""
    hold = cache.get(_key(model_key, record_id))
    return hold if hold and hold.get('until', 0) > _now_ms() else None


def _answer(hold: dict, contact_id) -> dict:
    return {'mine': hold['contact_id'] == contact_id, 'held_by': hold['name'],
            'until': _iso(hold['until']), 'minutes': hold['minutes']}


def take(actor, model_key: str, record_id) -> dict:
    """Take or extend the hold; if another person has it, say who and until when."""
    contact_id = getattr(actor, 'user_id', None)
    if not contact_id:
        raise Refused(400, 'hold_needs_a_person', 'A hold is a person editing; this request names no one.')
    current = holder(model_key, record_id)
    if current and current['contact_id'] != contact_id:
        return _answer(current, contact_id)
    previous = cache.get(_mine_key(contact_id, model_key))
    if previous is not None and str(previous) != str(record_id):
        mine = cache.get(_key(model_key, previous))
        if mine and mine.get('contact_id') == contact_id:
            cache.delete(_key(model_key, previous))      # loading another record releases this one
    span = minutes()
    user = getattr(actor, 'user', None)
    name = (' '.join(filter(None, [getattr(user, 'name_first', ''), getattr(user, 'name_last', '')]))
            or getattr(user, 'email', '') or f'Contact {contact_id}')
    hold = {'contact_id': contact_id, 'name': name, 'until': _now_ms() + span * 60_000, 'minutes': span}
    cache.set(_key(model_key, record_id), hold, timeout=span * 60)
    cache.set(_mine_key(contact_id, model_key), record_id, timeout=span * 60)
    return _answer(hold, contact_id)


def release(actor, model_key: str, record_id) -> dict:
    contact_id = getattr(actor, 'user_id', None)
    current = holder(model_key, record_id)
    if current and current['contact_id'] == contact_id:
        cache.delete(_key(model_key, record_id))
        cache.delete(_mine_key(contact_id, model_key))
        return {'released': True}
    return {'released': False}


def check(actor, model_key: str, record_id) -> None:
    """A save of a record someone else holds is refused, with who and until when."""
    current = holder(model_key, record_id)
    if current and current['contact_id'] != getattr(actor, 'user_id', None):
        until = datetime.fromtimestamp(current['until'] / 1000, timezone.utc)
        raise Refused(423, 'held', f"{current['name']} is editing this record until "
                                   f"{until.strftime('%H:%M')} UTC. It opens when they leave it or "
                                   f"the hold runs out.",
                      {'held_by': current['name'], 'until': _iso(current['until'])})


def hold_command(ctx) -> dict:
    return take(ctx.actor, ctx.model_key, ctx.obj.pk)


def release_command(ctx) -> dict:
    return release(ctx.actor, ctx.model_key, ctx.obj.pk)


def register() -> None:
    from apps.core.constants.model_registry import MODEL_REGISTRY
    from apps.core.services.verbs import register_command
    for model_key in MODEL_REGISTRY:
        register_command(model_key, 'hold', hold_command)
        register_command(model_key, 'release', release_command)
