"""Athena's local hook clearance.

WCHQ review is the safe road, not a toll gate. An installation owns its own
system, so Athena — the local one, on this box — will review a hook herself and
offer a token if the superuser wants it. Nobody has to ask permission to run code
on their own machine.

What Athena does before offering:

  * validates the payload against the local registry;
  * runs it against an empty record with every write simulated, and reports what
    it would set, create, log and call;
  * names her concerns: does it block saves, write authority fields, chain wide.

Then she offers. ``offer()`` reports; ``accept()`` issues the token and records who
accepted and what Athena had said at the time. Concerns do not prevent acceptance —
they are recorded alongside the name of the person who accepted them.

A locally issued token is signed with a key derived from this installation's
SECRET_KEY. It is worth nothing anywhere else: carrying a hook to another
installation means clearing it there, by WCHQ or by that box's own Athena.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

AUTHORITY_HINTS = ('is_superuser', 'is_staff', 'role', 'groups', 'permission', 'password',
                   'security_level', 'price', 'total', 'amount', 'gl_', 'balance')


def offer(report) -> Dict[str, Any]:
    """Review a hook locally and say what a token would be covering."""
    from apps.core.services.report_hooks import (ISSUER_ATHENA, dry_run, expected_token,
                                                 hook_hash, validate_hooks)

    hooks = (report.config or {}).get('hooks') or {}
    problems = validate_hooks(hooks)
    if problems:
        return {'ok': False, 'problems': problems,
                'message': 'The hook does not validate — nothing to clear yet.'}

    point = hooks.get('point') or ''
    model_key = point.split('.')[0] if '.' in point else ''
    runs = {phase: dry_run(hooks, model_key=model_key, phase=phase)
            for phase in ('before', 'during', 'after') if hooks.get(phase)}

    concerns = _concerns(runs)
    payload_hash = hook_hash(hooks)
    return {
        'ok': True,
        'issuer': ISSUER_ATHENA,
        'hook_hash': payload_hash,
        'simulation': runs,
        'concerns': concerns,
        'token_available': bool(expected_token(payload_hash, ISSUER_ATHENA)),
        'message': ('Athena has no concerns. A local token is available.' if not concerns
                    else f'Athena has {len(concerns)} concern(s). A local token is still '
                         'available if you accept them.'),
    }


def accept(report, by, reason: str = '') -> Dict[str, Any]:
    """Issue the local token. Superuser only; who accepted is written down."""
    from apps.core.services.report_hooks import ISSUER_ATHENA, apply_clearance, expected_token

    if not (by and getattr(by, 'is_superuser', False)):
        return {'ok': False, 'problems': ['local clearance requires a superuser']}

    reviewed = offer(report)
    if not reviewed.get('ok'):
        return {'ok': False, 'problems': reviewed.get('problems', [])}

    token = expected_token(reviewed['hook_hash'], ISSUER_ATHENA)
    if not token:
        return {'ok': False, 'problems': ['this installation has no SECRET_KEY to sign with']}

    applied = apply_clearance(
        report, token, issuer=ISSUER_ATHENA,
        accepted_by=str(getattr(by, 'email', '') or getattr(by, 'pk', '')),
        accepted_reason=reason,
        accepted_concerns=reviewed['concerns'],
    )
    if applied.get('status') != 'cleared':
        return {'ok': False, 'problems': applied.get('problems', [])}

    _record(report, reviewed, by, reason)
    logger.info('[ATHENA] %s cleared locally by %s (%d concern(s))',
                report.ida, getattr(by, 'email', by), len(reviewed['concerns']))
    return {'ok': True, 'status': 'cleared', 'issuer': ISSUER_ATHENA,
            'hash': applied['hash'], 'concerns': reviewed['concerns']}


def withdraw(report, by, reason: str = '') -> Dict[str, Any]:
    """Take back a local clearance. The hook stops at once."""
    from apps.ai_assistant.services.hook_review import STATE_REVOKED, _set_state, observe

    if not (by and getattr(by, 'is_superuser', False)):
        return {'ok': False, 'problems': ['withdrawing clearance requires a superuser']}

    _set_state(report, STATE_REVOKED, cleared=False, token='', revoked_reason=reason,
               revoked_by=str(getattr(by, 'email', '') or getattr(by, 'pk', '')))
    observe('alert', f'{report.ida}: local clearance withdrawn — hook stopped',
            detail=reason, report=report)
    return {'ok': True, 'status': STATE_REVOKED}


def _concerns(runs: Dict[str, dict]) -> List[dict]:
    concerns = []
    for phase, outcome in runs.items():
        if outcome.get('blocked'):
            concerns.append({'kind': 'blocks_saves',
                             'detail': f"{phase} can stop a save: {outcome['blocked']}"})
        for path in outcome.get('would_set', []):
            if any(hint in path.lower() for hint in AUTHORITY_HINTS):
                concerns.append({'kind': 'writes_authority', 'detail': f'{phase} writes {path}'})
        if len(outcome.get('would_call', [])) > 2:
            concerns.append({'kind': 'wide_chain',
                             'detail': f"{phase} calls {outcome['would_call']}"})
        for problem in outcome.get('problems', []):
            concerns.append({'kind': 'test_failed', 'detail': f'{phase}: {problem}'})
    return concerns


def _record(report, reviewed, by, reason) -> None:
    """Alice keeps the local decision beside the WCHQ ones, so the ledger of what
    runs here has one shape however it was cleared."""
    from apps.ai_assistant.services.hook_review import STATE_CLEARED, _set_state, observe

    _set_state(report, STATE_CLEARED, issuer='athena',
               accepted_by=str(getattr(by, 'email', '') or getattr(by, 'pk', '')))
    detail = reason or ''
    if reviewed['concerns']:
        detail = f"{detail} — accepted concerns: " + \
            '; '.join(c['detail'] for c in reviewed['concerns'])
    observe('alert' if reviewed['concerns'] else 'pattern',
            f'{report.ida}: cleared locally by Athena ({getattr(by, "email", by)})',
            detail=detail, report=report)
