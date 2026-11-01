"""The parades' feedback on a model (Bill, 2026-11-01: parade-list and parade-form walk each
model; the reviewer marks it Keep / Modify / Don't Need with a note).

Kept on the model's definition (its wc:model Setting) in prefs.parades.<parade> — beside, not in,
prefs.parade_feedback, which is parade-setting's review of the Setting itself. Plan 100 moves every
parade's notes to Actions in the flight-simulator project; until then this is where they live.

POST /wcapi/setting/<definition id>/parade_feedback/   {parade, decision, notes}
"""
from __future__ import annotations

from datetime import datetime, timezone

PARADES = ('list', 'form')
DECISIONS = ('keep', 'modify', 'dont_need')


def parade_feedback(ctx) -> dict:
    from apps.core.models import Setting
    from apps.core.services.door import Refused
    obj = ctx.obj
    if obj is None or getattr(obj, 'purpose', None) != 'wc:model':
        raise Refused(400, 'not_a_definition', "A model's parade feedback belongs to its definition (a wc:model Setting).")
    parade, decision = ctx.data.get('parade'), ctx.data.get('decision')
    if parade not in PARADES:
        raise Refused(400, 'parade_unknown', f"parade is one of {', '.join(PARADES)}.")
    if decision not in DECISIONS:
        raise Refused(400, 'decision_unknown', f"decision is one of {', '.join(DECISIONS)}.")
    user = getattr(ctx.actor, 'user', None)
    prefs = dict(obj.prefs or {})
    parades = dict(prefs.get('parades') or {})
    parades[parade] = {'decision': decision, 'notes': str(ctx.data.get('notes') or '')[:2000],
                       'user_id': getattr(user, 'pk', None),
                       'dt_feedback': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
    prefs['parades'] = parades
    Setting.objects.filter(pk=obj.pk).update(prefs=prefs)
    return {'model': obj.parent_model, 'parade': parade, 'feedback': parades[parade]}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('setting', 'parade_feedback', parade_feedback)
