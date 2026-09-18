"""Hook review — Alice's send and receive protocol with WCHQ.

Alice owns both ends of this exchange. On the instance she packages a hook, sends
it, tracks what is outstanding, applies the answer and records what happened. At
WCHQ the same protocol arrives as a bundle for the team to confirm, and her answer
comes back the same way.

The exchange is four messages, all carried as Bundles on ``wchq-conn-upstream``:

    hook.review.request   instance → WCHQ   this payload, this instance, confirm it
    hook.review.ack       WCHQ → instance   received, under review
    hook.review.answer    WCHQ → instance   cleared (token) | denied (reason)
    hook.review.revoke    WCHQ → instance   a cleared hook is no longer trusted

State lives on the report at ``config.hooks.athena.state``:

    draft → submitted → under_review → cleared | denied
    cleared → revoked  (WCHQ may withdraw trust at any time)

Only ``cleared`` runs, and only while the stored token still verifies against the
stored payload. Everything else is visible, never silent.

There is always a WCHQ connection record. An instance may choose never to use it —
a connection whose transport is ``manual`` writes the bundle for a person to carry —
but the record exists, because a missing connection is a fault, not a mode.
"""
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

WCHQ_CONNECTION_IDA = 'wchq-conn-upstream'

KIND_REQUEST = 'hook.review.request'
KIND_ACK = 'hook.review.ack'
KIND_ANSWER = 'hook.review.answer'
KIND_REVOKE = 'hook.review.revoke'

STATE_DRAFT = 'draft'
STATE_SUBMITTED = 'submitted'
STATE_UNDER_REVIEW = 'under_review'
STATE_CLEARED = 'cleared'
STATE_DENIED = 'denied'
STATE_REVOKED = 'revoked'


# ── connection ───────────────────────────────────────────────────────────────

def wchq_connection():
    """The WCHQ connection. Always expected to exist; seeded by seed_connections."""
    from apps.sync.models.connection import Connection
    return Connection.objects.filter(ida=WCHQ_CONNECTION_IDA, is_active=True).first()


def _no_connection_fault(report_ida: str) -> dict:
    observe('alert', f'No {WCHQ_CONNECTION_IDA} connection — hook review for {report_ida} cannot be sent',
            detail='Run: python manage.py seed_connections', priority=PRIORITY_IMPORTANT)
    return {'ok': False, 'error': 'no_wchq_connection',
            'message': f'{WCHQ_CONNECTION_IDA} is missing. Run seed_connections.'}


# ── Alice's record of what happened ──────────────────────────────────────────

PRIORITY_NORMAL, PRIORITY_IMPORTANT = 0, 1


def observe(category: str, message: str, detail: str = '', priority: int = PRIORITY_NORMAL,
            report=None) -> None:
    """Alice writes down every step of the exchange, so an unanswered review is
    visible without anyone remembering to look.

    Written in its own transaction: a failed observation must never poison the
    exchange it is describing.
    """
    from django.db import transaction
    try:
        from apps.ai_assistant.models.alice import AliceObservation
        with transaction.atomic():
            AliceObservation.objects.create(
                category=category, source='alice', priority=priority,
                message=message[:500], detail=detail[:2000],
                model_name='report' if report is not None else '',
                record_id=str(getattr(report, 'pk', '') or ''),
                dedup_key=f'hook_review:{getattr(report, "ida", "")}:{message[:60]}',
            )
    except Exception:  # observation must never break the exchange
        logger.exception('[HOOK REVIEW] could not write observation')


# ── state on the report ──────────────────────────────────────────────────────

def _set_state(report, state: str, **fields) -> None:
    from apps.core.services.report_hooks import hook_hash
    hooks = dict((report.config or {}).get('hooks') or {})
    athena = dict(hooks.get('athena') or {})
    athena.update(fields)
    athena['state'] = state
    athena.setdefault('required', True)
    history = list(athena.get('history') or [])[-19:]
    history.append({'state': state, 'dt_utc': int(time.time() * 1000),
                    'hash': hook_hash(hooks)})
    athena['history'] = history
    hooks['athena'] = athena
    report.config = {**(report.config or {}), 'hooks': hooks}
    report._hooks_authorized = True
    report.save(update_fields=['config', 'dt_modified'])


def review_state(report) -> str:
    hooks = (report.config or {}).get('hooks') or {}
    return ((hooks.get('athena') or {}).get('state')) or STATE_DRAFT


def outstanding_reviews():
    """Every hook Alice is waiting on an answer for."""
    from apps.core.models import Report
    waiting = []
    for report in Report.objects.filter(is_active=True, is_deleted=False,
                                        config__hooks__isnull=False):
        if review_state(report) in (STATE_SUBMITTED, STATE_UNDER_REVIEW):
            waiting.append(report)
    return waiting


# ── send ─────────────────────────────────────────────────────────────────────

def send_review_request(report, note: str = '') -> Dict[str, Any]:
    """Alice packages a hook and sends it to WCHQ for confirmation."""
    from apps.core.services.report_hooks import hook_hash, validate_hooks, _instance_uuid

    hooks = (report.config or {}).get('hooks') or {}
    problems = validate_hooks(hooks)
    if problems:
        observe('alert', f'{report.ida}: hook did not validate — not sent',
                detail='; '.join(problems), priority=PRIORITY_IMPORTANT, report=report)
        return {'ok': False, 'error': 'invalid_hooks', 'problems': problems}

    connection = wchq_connection()
    if not connection:
        return _no_connection_fault(report.ida)

    payload = {
        'content_type': 'hook_review',
        'endpoint': '/wcapi/hooks/submit/',
        'kind': KIND_REQUEST,
        'instance_uuid': _instance_uuid(),
        'report_ida': report.ida,
        'report_name': report.name or '',
        'hook_hash': hook_hash(hooks),
        'hooks': {k: v for k, v in hooks.items() if k != 'athena'},
        'note': note,
    }

    transport = (connection.config or {}).get('transport', 'api')
    if transport == 'manual':
        result = _write_for_carrying(connection, report, payload)
    else:
        result = _queue_bundle(connection, report, payload)

    _set_state(report, STATE_SUBMITTED, submitted_hash=payload['hook_hash'],
               submitted_via=transport)
    observe('pattern', f'{report.ida}: hook review sent to WCHQ ({transport})',
            detail=f"hash {payload['hook_hash'][:12]}", report=report)
    return result


def _queue_bundle(connection, report, payload) -> dict:
    """Queue through the standard outbound road: encrypted, ordered, retried."""
    from apps.core.models.pending import Pending
    pending = Pending.objects.create(
        purpose='sync.bundle_out',
        model_name='report',
        record_id=str(report.pk),
        name=f'hook review {report.ida}',
        config={'connection_id': connection.pk, 'model_name': 'report', 'payload': payload},
    )
    return {'ok': True, 'status': STATE_SUBMITTED, 'pending_uuid': str(pending.uuid),
            'hook_hash': payload['hook_hash']}


def _write_for_carrying(connection, report, payload) -> dict:
    """A manual-transport connection still records the exchange — the bundle is
    written where a person can carry it."""
    from apps.sync.models.bundle import Bundle
    bundle = Bundle.objects.create(
        connection=connection, direction='outbound', purpose='hook_review',
        status='exported', model_name='report',
        config={'report_ida': report.ida, 'hook_hash': payload['hook_hash']},
    )
    bundle.save_payload_to_disk(payload)
    return {'ok': True, 'status': STATE_SUBMITTED, 'bundle_id': bundle.pk,
            'path': (bundle.config or {}).get('payload_path', ''),
            'hook_hash': payload['hook_hash']}


# ── receive ──────────────────────────────────────────────────────────────────

def receive(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Alice receives a WCHQ message — ack, answer or revoke — from any route.

    Nothing here trusts the route. A clearance is applied only when the token
    verifies locally against the payload this instance has stored.
    """
    from apps.core.models import Report
    from apps.core.services.report_hooks import apply_clearance, hook_hash

    kind = (payload or {}).get('kind') or KIND_ANSWER
    ida = (payload or {}).get('report_ida')
    if not ida:
        return {'ok': False, 'error': 'report_ida is required'}

    report = Report.objects.filter(ida=ida, is_active=True, is_deleted=False).first()
    if not report:
        return {'ok': False, 'error': f"report '{ida}' not found"}

    stated = (payload or {}).get('hook_hash')
    current = hook_hash((report.config or {}).get('hooks') or {})
    if stated and stated != current:
        observe('alert', f'{ida}: answer is for a different payload — ignored',
                detail=f'answer {stated[:12]}, stored {current[:12]}',
                priority=PRIORITY_IMPORTANT, report=report)
        return {'ok': False, 'error': 'hash_mismatch'}

    if kind == KIND_ACK:
        _set_state(report, STATE_UNDER_REVIEW, reviewer=(payload.get('reviewer') or ''))
        observe('pattern', f'{ida}: WCHQ is reviewing the hook', report=report)
        return {'ok': True, 'status': STATE_UNDER_REVIEW}

    if kind == KIND_REVOKE:
        _set_state(report, STATE_REVOKED, cleared=False, token='',
                   revoked_reason=(payload.get('reason') or ''))
        observe('alert', f'{ida}: WCHQ revoked clearance — hook stopped',
                detail=payload.get('reason', ''), priority=PRIORITY_IMPORTANT, report=report)
        return {'ok': True, 'status': STATE_REVOKED}

    # hook.review.answer
    if not payload.get('token'):
        _set_state(report, STATE_DENIED, cleared=False, token='',
                   denied_reason=(payload.get('reason') or ''))
        observe('alert', f'{ida}: WCHQ denied the hook',
                detail=payload.get('reason', ''), priority=PRIORITY_IMPORTANT, report=report)
        return {'ok': True, 'status': STATE_DENIED, 'reason': payload.get('reason', '')}

    applied = apply_clearance(report, payload['token'])
    if applied.get('status') != 'cleared':
        observe('alert', f'{ida}: clearance refused — token did not verify here',
                detail='; '.join(applied.get('problems', [])), priority=PRIORITY_IMPORTANT, report=report)
        return {'ok': False, 'error': 'token_invalid', 'problems': applied.get('problems', [])}

    report.refresh_from_db()
    _set_state(report, STATE_CLEARED, cleared=True, token=payload['token'],
               hash=applied['hash'], reviewer=(payload.get('reviewer') or ''))
    observe('pattern', f'{ida}: cleared by WCHQ — hook is live', report=report)
    return {'ok': True, 'status': STATE_CLEARED, 'hash': applied['hash']}


def receive_from_file(path: str) -> Dict[str, Any]:
    """Apply an answer carried in by hand (manual transport)."""
    import json
    with open(path) as handle:
        return receive(json.load(handle))
