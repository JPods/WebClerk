"""Lock and unlock a document by hand (Bill, 2026-09-29).

A person locks a transaction document; it is not an event of its own. The lock is a rich object
— who and when, not a boolean — in ``metadata.health.lock``, and the document's ``status`` is
``locked`` while it holds:

    metadata.health.lock = {"dt": <UTC ms>, "by": {"id": n, "name": "…"}, "reason": "…",
                            "status_before": "open"}

Unlock restores ``status_before`` and moves the lock, with who lifted it and why, to
``metadata.health.lock_history``. Only these two commands write either; the door refuses them
in a payload, and refuses ``status: locked`` set by hand.

    POST /wcapi/<quote|order|invoice|purchase|receipt>/<id>/lock/   {"reason": "…"}
    POST /wcapi/<…>/<id>/unlock/                                   {"reason": "…"}

Who: any staff role that may edit the document locks it (the command gate); admins and
superusers unlock. While locked, payments still apply (add_cash, apply_balance, and cash
applications, which do not save the document through the door) and comments can be added;
every other save, line change, delete and command is refused with coaching naming who locked
it, when and why. Workorders are left out while they are frozen.
Spec: ~/Allie/readmes/assessments/2026-09-29-document-lock-spec.md
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from apps.core.services.door import Refused

LOCKABLE_MODELS = ('quote', 'order', 'invoice', 'purchase', 'receipt')
#: Commands a locked document still answers: its unlock, and money arriving.
COMMANDS_WHILE_LOCKED = frozenset({'unlock', 'add_cash', 'apply_balance'})
#: What a save to a locked document may carry: the record's address, its version, comments.
SAVE_KEYS_WHILE_LOCKED = frozenset({'id', 'version', 'model_name', 'comments'})
LOCKED = 'locked'


def lock_of(obj) -> Optional[Dict[str, Any]]:
    """The document's current lock, or None."""
    health = ((getattr(obj, 'metadata', None) or {}).get('health') or {})
    lock = health.get('lock')
    return lock if isinstance(lock, dict) and lock else None


def _who(actor) -> Dict[str, Any]:
    user = getattr(actor, 'user', None)
    name = ' '.join(p for p in (getattr(user, 'name_first', ''), getattr(user, 'name_last', ''))
                    if p).strip() or getattr(user, 'email', '') or actor.kind
    return {'id': getattr(user, 'pk', None), 'name': name}


def _when(ms: int) -> str:
    return time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(ms / 1000))


def locked_coaching(model_key: str, obj, lock: Dict[str, Any]) -> str:
    by = (lock.get('by') or {}).get('name') or 'someone'
    return (f'{model_key} {getattr(obj, "ida", None) or obj.pk} is locked — by {by} on '
            f'{_when(int(lock.get("dt") or 0))}: {lock.get("reason") or "no reason given"}. '
            f'Comments and payments still go through; an admin or superuser can unlock it.')


def _reason(ctx) -> str:
    reason = str((ctx.data or {}).get('reason') or '').strip()
    if not reason:
        raise Refused(400, 'reason_required', f'Say why: {{"reason": "…"}}.', ctx.model_key)
    return reason


def _write(obj, metadata: dict, status: str) -> None:
    obj.metadata = metadata
    obj.status = status
    obj.save(update_fields=['metadata', 'status', 'dt_modified', 'version'])


def lock(ctx) -> Dict[str, Any]:
    obj = ctx.obj
    reason = _reason(ctx)
    held = lock_of(obj)
    if held:
        raise Refused(409, 'already_locked', locked_coaching(ctx.model_key, obj, held),
                      {'lock': held})
    entry = {'dt': int(time.time() * 1000), 'by': _who(ctx.actor), 'reason': reason,
             'status_before': obj.status or ''}
    metadata = dict(obj.metadata or {})
    metadata['health'] = {**(metadata.get('health') or {}), 'lock': entry}
    _write(obj, metadata, LOCKED)
    return {'id': obj.pk, 'lock': entry, 'status': LOCKED}


def unlock(ctx) -> Dict[str, Any]:
    from apps.core.services import access
    obj = ctx.obj
    if not access.is_admin(ctx.actor):
        raise Refused(403, 'unlock_not_permitted',
                      'An admin or superuser unlocks a document. Ask one, or send a support note.',
                      ctx.model_key)
    reason = _reason(ctx)
    held = lock_of(obj)
    if not held:
        raise Refused(409, 'not_locked', f'{ctx.model_key} {obj.pk} is not locked.', obj.pk)
    closed = {**held, 'unlocked_dt': int(time.time() * 1000), 'unlocked_by': _who(ctx.actor),
              'unlock_reason': reason}
    metadata = dict(obj.metadata or {})
    health = dict(metadata.get('health') or {})
    health.pop('lock', None)
    health['lock_history'] = list(health.get('lock_history') or []) + [closed]
    metadata['health'] = health
    _write(obj, metadata, held.get('status_before') or 'planned')
    return {'id': obj.pk, 'status': obj.status, 'unlocked': closed}


def refuse_if_locked(ctx, document=None) -> None:
    """Before any verb on a lockable document (or one of its lines): refuse what a lock stops.

    Also, locked or not, a payload never writes the lock itself or sets status 'locked'."""
    data = ctx.data or {}
    health = ((data.get('metadata') or {}).get('health') or {}) if isinstance(data.get('metadata'), dict) else {}
    if 'lock' in health or 'lock_history' in health:
        raise Refused(400, 'lock_by_command',
                      'A lock is set and lifted by the lock and unlock commands, not in a save.',
                      ctx.model_key)
    if document is None and data.get('status') == LOCKED and ctx.verb in ('save', 'new'):
        raise Refused(400, 'lock_by_command',
                      f'Lock a document with POST /wcapi/{ctx.model_key}/<id>/lock/ {{"reason": "…"}}.',
                      ctx.model_key)
    doc = document if document is not None else ctx.obj
    if doc is None or not getattr(doc, 'pk', None):
        return
    held = lock_of(doc)
    if not held or not ctx.actor.is_guarded:
        return
    doc_key = getattr(getattr(doc, '_meta', None), 'model_name', ctx.model_key)
    if ctx.verb in COMMANDS_WHILE_LOCKED and document is None:
        return
    if ctx.verb == 'save' and document is None:
        extra = {k for k in data if not k.startswith('_')} - SAVE_KEYS_WHILE_LOCKED
        if not extra:
            return
    raise Refused(409, 'document_locked', locked_coaching(doc_key, doc, held), {'lock': held})


def register() -> None:
    from apps.core.services.verbs import register_command
    for model_key in LOCKABLE_MODELS:
        register_command(model_key, 'lock', lock)
        register_command(model_key, 'unlock', unlock)
