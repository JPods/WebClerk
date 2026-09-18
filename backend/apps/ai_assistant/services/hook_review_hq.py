"""Hook review at WCHQ — Alice's side of the exchange.

A request arrives and is worked immediately. Alice does not sit on it:

  1. **Structure** — the payload must validate, and every verb must be one WebClerk
     knows. An unknown key is refused here, not discovered later.
  2. **Test functions** — the hook is run against an empty record with every write
     simulated, so the answer includes what it *would* set, create, log and call.
     Nothing is saved, nowhere.
  3. **The council** — Alice has standing authority to ask, and asks in this order:
       Athena  — safety: does this reach past its point, write authority fields,
                 chain far, or log where it should not? Deterministic, always runs.
       Allie   — cross-domain: has this pattern bitten another installation?
       Claude  — code review: does the rule do what its author thinks it does?
     Allie and Claude are asked only when they are reachable. An unreachable
     adviser is a recorded gap, never a silent pass.
  4. **The decision** — clean and unanimous means Alice signs the token and answers
     at once. Any question at all means a human signs off first: the request is
     held as a Document at WCHQ with the findings attached, and nothing goes back
     until a person approves or denies it.

Straightforward hooks come back in seconds. Anything with a question waits for a
person. That division is the whole design.
"""
import json
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Findings that always need a person, whatever the council says.
ALWAYS_ASK_A_HUMAN = (
    'blocks_saves',        # a rule that can stop people working
    'writes_authority',    # anything near permissions, roles, prices
    'unknown_point',       # a point WCHQ has never seen
)

AUTHORITY_HINTS = ('is_superuser', 'is_staff', 'role', 'groups', 'permission', 'password',
                   'security_level', 'price', 'total', 'amount', 'gl_', 'balance')


def review_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Work a hook.review.request the moment it lands.

    Returns either an answer to send back now, or a held review awaiting sign-off.
    """
    started = time.perf_counter()
    hooks = (payload or {}).get('hooks') or {}
    ida = (payload or {}).get('report_ida') or ''
    instance_uuid = (payload or {}).get('instance_uuid') or ''

    findings: List[dict] = []
    findings += _structure_findings(hooks)
    simulation = _test_functions(hooks)
    findings += [{'kind': 'test_failed', 'by': 'tests', 'detail': p}
                 for p in simulation.get('problems', [])]
    findings += _athena_findings(hooks, simulation)
    findings += _ask_adviser('allie', hooks, payload)
    findings += _ask_adviser('claude', hooks, payload)

    questions = [f for f in findings if f.get('kind') != 'note']
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    record = _hold_for_record(payload, findings, simulation, elapsed_ms,
                              held=bool(questions))

    if questions:
        logger.info('[HQ HOOK] %s held for sign-off (%d question(s))', ida, len(questions))
        return {'status': 'held', 'kind': 'hook.review.ack', 'report_ida': ida,
                'hook_hash': payload.get('hook_hash', ''), 'review_id': record,
                'questions': questions, 'simulation': simulation, 'elapsed_ms': elapsed_ms}

    answer = sign_answer(instance_uuid, payload.get('hook_hash', ''), ida,
                         reviewer='wchq-alice')
    logger.info('[HQ HOOK] %s cleared automatically in %dms', ida, elapsed_ms)
    answer.update({'simulation': simulation, 'elapsed_ms': elapsed_ms, 'review_id': record})
    return answer


# ── 1. structure ─────────────────────────────────────────────────────────────

def _structure_findings(hooks: dict) -> List[dict]:
    from apps.core.services.report_hooks import VERBS, CONDITIONS, MODIFIERS

    findings = []
    point = hooks.get('point') or ''
    if not point or '.' not in point:
        findings.append({'kind': 'unknown_point', 'by': 'structure',
                         'detail': f"point '{point}' is not a model.phase pair"})
    known = set(VERBS) | set(CONDITIONS) | set(MODIFIERS)
    for phase in ('before', 'during', 'after'):
        for index, rule in enumerate(hooks.get(phase) or []):
            if not isinstance(rule, dict):
                findings.append({'kind': 'malformed', 'by': 'structure',
                                 'detail': f'{phase}[{index}] is not an object'})
                continue
            unknown = set(rule) - known
            if unknown:
                findings.append({'kind': 'unknown_verb', 'by': 'structure',
                                 'detail': f'{phase}[{index}]: {sorted(unknown)}'})
    return findings


# ── 2. test functions ────────────────────────────────────────────────────────

def _test_functions(hooks: dict) -> dict:
    """Run the hook with every write simulated and report what it would do."""
    from apps.core.services.report_hooks import dry_run

    point = hooks.get('point') or ''
    model_key = point.split('.')[0] if '.' in point else ''
    phases = [p for p in ('before', 'during', 'after') if hooks.get(p)]
    runs = {}
    problems: List[str] = []
    for phase in phases:
        outcome = dry_run(hooks, model_key=model_key, phase=phase)
        runs[phase] = outcome
        problems += outcome.get('problems', [])
    return {'runs': runs, 'problems': problems,
            'model': model_key, 'phases': phases}


# ── 3. the council ───────────────────────────────────────────────────────────

def _athena_findings(hooks: dict, simulation: dict) -> List[dict]:
    """Athena asks one question: can this reach further than it was given?"""
    findings = []
    for phase, outcome in (simulation.get('runs') or {}).items():
        if outcome.get('blocked'):
            findings.append({'kind': 'blocks_saves', 'by': 'athena',
                             'detail': f"{phase} can stop a save: {outcome['blocked']}"})
        for path in outcome.get('would_set', []):
            if any(hint in path.lower() for hint in AUTHORITY_HINTS):
                findings.append({'kind': 'writes_authority', 'by': 'athena',
                                 'detail': f'{phase} writes {path}'})
        if len(outcome.get('would_call', [])) > 2:
            findings.append({'kind': 'wide_chain', 'by': 'athena',
                             'detail': f"{phase} calls {outcome['would_call']}"})
    text = json.dumps(hooks)
    if '{{' in text and 'password' in text.lower():
        findings.append({'kind': 'writes_authority', 'by': 'athena',
                         'detail': 'a token in this hook references a password field'})
    return findings


def _ask_adviser(who: str, hooks: dict, payload: dict) -> List[dict]:
    """Ask Allie or Claude. Alice has standing authority to ask; an adviser that
    cannot be reached is recorded as a gap, not treated as approval."""
    question = (
        f"A WebClerk installation submitted this report hook for confirmation.\n"
        f"Point: {hooks.get('point')}\n"
        f"Rules: {json.dumps({k: v for k, v in hooks.items() if k != 'athena'}, indent=2)[:3000]}\n\n"
        "Does this do what its author appears to intend, and is there any reason a "
        "person should look at it before it is trusted? Answer in two sentences, and "
        "begin with CONCERN or CLEAR."
    )
    try:
        answer = _consult(who, question)
    except Exception as exc:
        return [{'kind': 'adviser_unreachable', 'by': who, 'detail': str(exc)[:200]}]

    if not answer:
        return [{'kind': 'adviser_unreachable', 'by': who, 'detail': 'no answer'}]
    if answer.strip().upper().startswith('CONCERN'):
        return [{'kind': 'adviser_concern', 'by': who, 'detail': answer[:500]}]
    return [{'kind': 'note', 'by': who, 'detail': answer[:500]}]


def _consult(who: str, question: str) -> str:
    """Allie answers through the local model; Claude through WCHQ escalation."""
    if who == 'allie':
        from apps.ai_assistant.services.ollama_client import OllamaClient
        return (OllamaClient().generate(question) or '').strip()
    if who == 'claude':
        from apps.ai_assistant.services.escalation import escalate_to_wchq
        reply = escalate_to_wchq(question=question, local_answer='', local_confidence=0.0,
                                 context='hook review', mode='review')
        return (reply or {}).get('answer', '').strip()
    raise ValueError(f'unknown adviser {who}')


# ── 4. the decision ──────────────────────────────────────────────────────────

def sign_answer(instance_uuid: str, hook_hash: str, report_ida: str,
                reviewer: str = 'wchq') -> Dict[str, Any]:
    """Sign the token that binds one payload to one instance."""
    import hashlib
    import hmac
    from apps.ai_assistant.services.hook_review import wchq_connection

    connection = wchq_connection()
    secret = ((connection.config or {}).get('athena_token') or '') if connection else ''
    if not secret:
        return {'status': 'error', 'problems': ['no athena token to sign with']}

    token = hmac.new(secret.encode(), f'{instance_uuid}:{hook_hash}'.encode(),
                     hashlib.sha256).hexdigest()
    return {'status': 'cleared', 'kind': 'hook.review.answer', 'report_ida': report_ida,
            'hook_hash': hook_hash, 'token': token, 'reviewer': reviewer}


def _hold_for_record(payload: dict, findings: list, simulation: dict, elapsed_ms: int,
                     held: bool) -> str:
    """Every review is written down at WCHQ. A held one is what a person signs."""
    try:
        from apps.docs.models.document import Document
        doc = Document.objects.create(
            name=f"Hook review {payload.get('report_ida', '?')}",
            config={
                'purpose': 'hook_review',
                'status': 'awaiting_signoff' if held else 'auto_cleared',
                'instance_uuid': payload.get('instance_uuid', ''),
                'report_ida': payload.get('report_ida', ''),
                'hook_hash': payload.get('hook_hash', ''),
                'hooks': payload.get('hooks', {}),
                'note': payload.get('note', ''),
                'findings': findings,
                'simulation': simulation,
                'elapsed_ms': elapsed_ms,
            },
        )
        return str(doc.ida or doc.pk)
    except Exception:
        logger.exception('[HQ HOOK] could not write the review record')
        return ''


def sign_off(review_id: str, approved: bool, by: str, reason: str = '') -> Dict[str, Any]:
    """A person at WCHQ approves or denies a held review, and the answer goes out."""
    from apps.docs.models.document import Document

    doc = Document.objects.filter(ida=review_id).first() or \
        Document.objects.filter(pk=review_id if str(review_id).isdigit() else 0).first()
    if not doc:
        return {'status': 'error', 'problems': [f'review {review_id} not found']}

    config = doc.config or {}
    if config.get('purpose') != 'hook_review':
        return {'status': 'error', 'problems': ['not a hook review record']}
    if config.get('status') != 'awaiting_signoff':
        return {'status': 'error', 'problems': [f"review is {config.get('status')}"]}

    if not approved:
        config.update({'status': 'denied', 'signed_off_by': by, 'reason': reason})
        doc.config = config
        doc.save(update_fields=['config', 'dt_modified'])
        return {'status': 'denied', 'kind': 'hook.review.answer',
                'report_ida': config.get('report_ida', ''),
                'hook_hash': config.get('hook_hash', ''), 'reason': reason, 'reviewer': by}

    answer = sign_answer(config.get('instance_uuid', ''), config.get('hook_hash', ''),
                         config.get('report_ida', ''), reviewer=by)
    config.update({'status': 'cleared', 'signed_off_by': by, 'reason': reason})
    doc.config = config
    doc.save(update_fields=['config', 'dt_modified'])
    return answer


def awaiting_signoff():
    """Reviews holding for a person at WCHQ."""
    from apps.docs.models.document import Document
    return Document.objects.filter(config__purpose='hook_review',
                                   config__status='awaiting_signoff')
