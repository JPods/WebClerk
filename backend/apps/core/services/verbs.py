"""The channel verbs — one route per verb, one structure per verb.

Bill, 2026-09-24 (Channel_Inheritance.png): every channel path is
``/wcapi/<verb>/<model_name>/``, and every verb runs the same structure:

    code before → user before → base service → code after → user after

The base service is one function for every model (``save_record``, ``delete_record``).
The code hooks are the model's ``ModelBehaviour`` (behaviours.py); the user hooks are the
one Report in the slot ``<model>.<verb>_<pre|post>`` (report_hooks.py). Hooks are
automatic: no caller invokes one and nothing skips one. A caller who wants a hook to
behave a particular way says so in the payload, as underscore signals the hook reads.
An after hook runs only when the base succeeded.

A verb is added here, never by writing a URL. The route-shape test holds every
``wcapi/`` route to this list. Plan: Allie ``readmes/assessments/2026-09-24-one-route-per-verb.md``.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any, Callable, Dict

from apps.core.services.behaviours import HookContext, behaviour_for
from apps.core.services.door import Actor, Refused

console_logger = logging.getLogger('console')


def _save(actor: Actor, model_key: str, payload: dict):
    from apps.core.services.save import save_record
    return save_record(actor, payload, model_key=model_key)


def _delete(actor: Actor, model_key: str, payload: dict):
    from apps.core.services.delete import delete_record
    return delete_record(actor, model_key, payload.get('id'))


#: The closed list. get joins in step 2; the commands (convert, receive, pay, refund,
#: reserve, release, adjust, recalc, run, export, import) as their base services are built.
VERBS: Dict[str, Callable[[Actor, str, dict], Any]] = {
    'save': _save,
    'delete': _delete,
}


def run(actor: Actor, verb: str, model_key: str, payload: dict):
    """Every channel's way in: an actor, a verb, a model, a payload."""
    base = VERBS.get(verb)
    if base is None:
        raise Refused(404, 'unknown_verb', f'{verb} is not a verb.', {'verbs': sorted(VERBS)})
    return base(actor, model_key, dict(payload or {}))


# ── the hooks around every base ───────────────────────────────────────

#: How many user hooks are running, one inside another. A user hook may write a record
#: (create_action); that record's code hooks run, and so does its own user hook — once.
#: A third level is refused, so a hook cannot feed itself (Fable review, 2026-09-24).
_USER_HOOK_DEPTH = contextvars.ContextVar('wc_user_hook_depth', default=0)
MAX_USER_HOOK_DEPTH = 2


def before(ctx: HookContext) -> None:
    """Code, then user. Either may refuse with ``Refused``."""
    behaviour_for(ctx.model_key).hook('before', ctx)
    _user_hook(ctx, 'pre')


def after(ctx: HookContext) -> None:
    """Code, then user — only ever called after the base succeeded."""
    behaviour_for(ctx.model_key).hook('after', ctx)
    _user_hook(ctx, 'post')


def _user_hook(ctx: HookContext, moment: str) -> None:
    from apps.core.services.report_hooks import (HookBlocked, HookSlotConflict,
                                                 hooks_for_point, run_hooks, slot_point)
    depth = _USER_HOOK_DEPTH.get()
    if depth >= MAX_USER_HOOK_DEPTH:
        point = slot_point(ctx.model_key, ctx.verb, moment)
        if hooks_for_point(point):
            raise Refused(409, 'hook_depth',
                          f'A hook wrote a {ctx.model_key} whose own hook would write again '
                          f'({point}). Hooks may nest {MAX_USER_HOOK_DEPTH} deep.',
                          {'point': point})
        return

    token = _USER_HOOK_DEPTH.set(depth + 1)
    try:
        result = run_hooks(ctx.model_key, ctx.verb, moment, ctx.obj, changed=set(ctx.changed),
                           user=ctx.user)
    except HookBlocked as blocked:
        raise Refused(400, 'hook_blocked', blocked.message, blocked.message,
                      extra={'report': blocked.report_ida})
    except HookSlotConflict as conflict:
        raise Refused(409, 'hook_slot_conflict', str(conflict),
                      {'point': conflict.point, 'reports': conflict.idas})
    finally:
        _USER_HOOK_DEPTH.reset(token)

    if moment == 'post' and result.set_fields and ctx.verb != 'delete':
        _save_hook_fields(ctx.obj, result.set_fields)
    if result.errors:
        note = '; '.join(result.errors)
        console_logger.warning('[HOOK] %s.%s_%s problems: %s', ctx.model_key, ctx.verb,
                               moment, note)
        if moment == 'post':
            ctx.messages.append(note)


def _save_hook_fields(obj, paths) -> None:
    """What a post rule set is written once, as the fields it touched — not a second full
    save outside the door."""
    fields = {str(p).split('.', 1)[0] for p in paths}
    names = {f.name for f in obj._meta.concrete_fields}
    update = sorted(fields & names)
    if not update:
        return
    update += [f for f in ('version', 'dt_modified') if f in names and f not in update]
    obj.save(update_fields=update)
