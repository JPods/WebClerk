"""Report hooks — the only executable surface in WebClerk.

A hook is data, not code. It lives on a Report record in ``config.hooks`` and is
run by this engine. There is no exec(): a hook can do exactly what the verb table
below allows, on exactly the fields the hook-point registry allows.

    config.hooks = {
        "point": "invoice.save_pre",
        "before": [ ...rules... ],     # once, on the selection
        "during": [ ...rules... ],     # per record, while gathered
        "after":  [ ...rules... ],     # per record, once results are known
    }

Rule shape (every key optional except the verb):

    {"when": {"status": "released"},        # condition — field equals value
     "when_changed": "status",              # condition — field changed this save
     "require": "terms_id",                 # validate — present and non-empty
     "match": {"email": "^[^@]+@[^@]+$"},   # validate — regex
     "range": {"margin_pct": [0, 100]},     # validate — inclusive bounds
     "block": "Released invoices need terms",   # stop the save (pre only)
     "set": {"metadata.review.flag": true},     # write a value or {{token}}
     "add_comment": "Flagged by {{report.ida}}",   # a process comment, stamped like a person's
     "add_comment": {"channel": "public", "text": "..."},
     "create_action": {"title": "...", "assigned_to": "{{rep_id}}"},
     "run_report": "RPT-OTHER"}             # chain — depth-limited, cycle-refused

Guard rails, in order of who says no first:
  1. Athena — hooks whose payload hash is not cleared by WCHQ do not run.
  2. Registry — the point must be declared; may_set / may_block / may_create /
     may_run bound what the rule may touch.
  3. Budget — a phase that exceeds its time budget is abandoned, and the hook is
     marked unhealthy rather than left to hang a save dialog.

Nothing here raises into a user's dialog except HookBlocked, which the save view
turns into an inline validation message.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Time budgets, in seconds, per verb moment and per report phase. A pre hook is in
# the caller's path, so it is the tightest; a get hook is on every read.
BUDGETS = {
    'save_pre': 0.25,
    'save_post': 1.0,
    'delete_pre': 0.25,
    'delete_post': 1.0,
    'get_pre': 0.1,
    'get_post': 0.25,
    'before': 5.0,
    'during': 5.0,
    'after': 30.0,
}

MAX_CHAIN_DEPTH = 5

RULE_ACTIONS = ('require', 'match', 'range', 'block', 'set', 'add_comment', 'create_action',
         'append_log', 'run_report')
CONDITIONS = ('when', 'when_changed')
MODIFIERS = ('message',)  # the text a failed validate shows the user

HOOK_POINTS_PURPOSE = 'wc:hook_points'


class HookBlocked(Exception):
    """A pre-save rule refused the save. Carries the message meant for the user."""

    def __init__(self, message: str, rule_index: int = -1, report_ida: str = ''):
        super().__init__(message)
        self.message = message
        self.rule_index = rule_index
        self.report_ida = report_ida


@dataclass
class HookResult:
    """What a phase did. Never raises for a bad rule — it records and moves on."""
    ran: List[str] = field(default_factory=list)
    set_fields: List[str] = field(default_factory=list)
    created: List[str] = field(default_factory=list)
    called: List[str] = field(default_factory=list)
    logged: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors and not self.timed_out


# ── payload hash + Athena clearance ──────────────────────────────────────────

def hook_hash(hooks: dict) -> str:
    """Stable sha256 of the hook payload. Any edit changes it, which drops
    Athena clearance — a cleared hook is cleared for exactly what WCHQ saw."""
    payload = {k: v for k, v in (hooks or {}).items() if k != 'athena'}
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def athena_state(report) -> dict:
    """Clearance block for a report's hooks: required / cleared / token / hash."""
    hooks = (report.config or {}).get('hooks') or {}
    state = dict(hooks.get('athena') or {})
    state.setdefault('required', True)
    state.setdefault('cleared', False)
    state['hash_now'] = hook_hash(hooks)
    state['hash_matches'] = bool(state.get('hash') and state['hash'] == state['hash_now'])
    return state


def is_cleared(report) -> bool:
    """Cleared means WCHQ confirmed THIS payload for THIS instance — the stored
    token has to verify, not merely exist."""
    state = athena_state(report)
    if not state['required']:
        return True
    if not (state.get('cleared') and state['hash_matches'] and state.get('token')):
        return False
    return token_valid(report)


# ── registry ─────────────────────────────────────────────────────────────────

def get_hook_points() -> dict:
    """Declared attach points. Superusers own this Setting; an undeclared point
    can neither be saved on a report nor run."""
    from apps.core.models import Setting
    setting = Setting.objects.filter(purpose=HOOK_POINTS_PURPOSE, is_active=True).first()
    if not setting or not isinstance(setting.config, dict):
        return {}
    points = setting.config.get('points')
    return points if isinstance(points, dict) else {}


def point_rules(point: str) -> Optional[dict]:
    return get_hook_points().get(point)


def _path_allowed(path: str, allowed: List[str]) -> bool:
    """`metadata.review.*` allows `metadata.review.flag`; an exact entry allows itself."""
    for pattern in allowed or []:
        if pattern == path:
            return True
        if pattern.endswith('.*') and path.startswith(pattern[:-1]):
            return True
        if pattern == '*':
            return True
    return False


# ── validation (used by the Report save gate and by WCHQ submission) ─────────

def validate_hooks(hooks: dict) -> List[str]:
    """Structural check of a hook payload against the registry. Returns problems;
    an empty list means the payload may be saved."""
    problems: List[str] = []
    if not isinstance(hooks, dict):
        return ['config.hooks must be an object']

    point = hooks.get('point')
    if not point:
        problems.append('config.hooks.point is required')
    declared = point_rules(point) if point else None
    if point and declared is None:
        problems.append(f"hook point '{point}' is not declared in {HOOK_POINTS_PURPOSE}")

    for phase in ('before', 'during', 'after'):
        rules = hooks.get(phase)
        if rules is None:
            continue
        if not isinstance(rules, list):
            problems.append(f'{phase} must be a list of rules')
            continue
        for i, rule in enumerate(rules):
            problems += _validate_rule(rule, phase, i, declared or {})
    return problems


def _validate_rule(rule: Any, phase: str, index: int, declared: dict) -> List[str]:
    where = f'{phase}[{index}]'
    if not isinstance(rule, dict):
        return [f'{where}: rule must be an object']
    problems = []
    unknown = set(rule) - set(RULE_ACTIONS) - set(CONDITIONS) - set(MODIFIERS)
    if unknown:
        problems.append(f"{where}: unknown key(s) {sorted(unknown)}")
    if not (set(rule) & set(RULE_ACTIONS)):
        problems.append(f'{where}: rule has no verb')

    if 'set' in rule:
        if not isinstance(rule['set'], dict):
            problems.append(f'{where}: set must be an object of path → value')
        else:
            for path in rule['set']:
                if not _path_allowed(path, declared.get('may_set', [])):
                    problems.append(f"{where}: set '{path}' is not allowed at this hook point")
    if 'block' in rule and not declared.get('may_block'):
        problems.append(f'{where}: this hook point may not block')
    if 'create_action' in rule and 'action' not in (declared.get('may_create') or []):
        problems.append(f'{where}: this hook point may not create actions')
    if 'add_comment' in rule:
        channel = _comment_channel(rule['add_comment'])
        if not _path_allowed(f'comments.{channel}', declared.get('may_set', [])):
            problems.append(f"{where}: add_comment writes comments.{channel}, which this hook "
                            f"point may not set")
    if 'append_log' in rule:
        spec = rule['append_log']
        name = spec.get('log') if isinstance(spec, dict) else spec
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9_-]{1,64}', name or ''):
            problems.append(f'{where}: append_log needs a log name of letters, digits, _ or -')
        elif name not in (declared.get('may_log') or []):
            problems.append(f"{where}: this hook point may not write log '{name}'")

    if 'run_report' in rule:
        may_run = declared.get('may_run') or []
        if rule['run_report'] not in may_run and '*' not in may_run:
            problems.append(f"{where}: may not call report '{rule['run_report']}'")
    return problems


# ── reading and writing record values ────────────────────────────────────────

def _read(record, path: str):
    """Dotted read: `status`, `totals.margin_pct`, `metadata.review.flag`."""
    parts = path.split('.')
    value = getattr(record, parts[0], None)
    for part in parts[1:]:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _write(record, path: str, value) -> None:
    parts = path.split('.')
    if len(parts) == 1:
        setattr(record, parts[0], value)
        return
    root = getattr(record, parts[0], None)
    if not isinstance(root, dict):
        root = {}
    node = root
    for part in parts[1:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value
    setattr(record, parts[0], root)


def _render(value, context: dict):
    """Resolve {{token}} against the run context. Non-strings pass through."""
    if not isinstance(value, str) or '{{' not in value:
        return value

    def sub(match):
        key = match.group(1).strip()
        found = context
        for part in key.split('.'):
            if isinstance(found, dict):
                found = found.get(part)
            else:
                found = None
                break
        return '' if found is None else str(found)

    return re.sub(r'\{\{([^}]+)\}\}', sub, value)


def _condition_holds(rule: dict, record, changed: set, context: dict) -> bool:
    when = rule.get('when')
    if isinstance(when, dict):
        for path, expected in when.items():
            if _read(record, path) != _render(expected, context):
                return False
    changed_field = rule.get('when_changed')
    if changed_field and changed_field not in (changed or set()):
        return False
    return True


# ── the runner ───────────────────────────────────────────────────────────────

def run_phase(
    report,
    phase: str,
    record=None,
    changed: Optional[set] = None,
    context: Optional[dict] = None,
    depth: int = 0,
    stack: Optional[List[str]] = None,
    user=None,
    simulate: bool = False,
    budget_key: Optional[str] = None,
) -> HookResult:
    """Run one phase of one report's hooks.

    Raises HookBlocked only for a `block` rule (pre-save). Every other failure is
    recorded in the result: a broken hook must not take a save down with it.
    """
    result = HookResult()
    hooks = (report.config or {}).get('hooks') or {}
    rules = hooks.get(phase)
    if not rules:
        return result

    ida = getattr(report, 'ida', '') or getattr(report, 'name', '?')
    stack = list(stack or [])

    # A simulation is how a hook gets looked at before it is trusted, so clearance
    # is checked for real runs only. A simulation writes nothing.
    if not simulate and not is_cleared(report):
        result.errors.append(f"{ida}: hooks not cleared by WCHQ/Athena — not run")
        return result

    declared = point_rules(hooks.get('point')) or {}
    budget = BUDGETS.get(budget_key or phase, BUDGETS['after'])
    started = time.monotonic()

    ctx = dict(context or {})
    ctx.setdefault('report', {'ida': ida, 'name': getattr(report, 'name', '')})
    if record is not None:
        ctx.setdefault('record', {'id': getattr(record, 'id', None)})

    for index, rule in enumerate(rules):
        if time.monotonic() - started > budget:
            result.timed_out = True
            result.errors.append(f'{ida}: {phase} exceeded {budget}s budget at rule {index}')
            _mark_unhealthy(report, f'{phase} over budget')
            break
        if not isinstance(rule, dict):
            result.errors.append(f'{ida}: {phase}[{index}] is not an object')
            continue
        if record is not None and not _condition_holds(rule, record, changed or set(), ctx):
            continue
        try:
            _apply_rule(rule, index, report, ida, record, declared, ctx, result, depth, stack,
                        user, simulate)
        except HookBlocked:
            raise
        except Exception as exc:  # a bad rule is a hook problem, not a save problem
            logger.exception('[HOOK] %s %s[%d] failed', ida, phase, index)
            result.errors.append(f'{ida}: {phase}[{index}] {type(exc).__name__}: {exc}')

    return result


def _apply_rule(rule, index, report, ida, record, declared, ctx, result, depth, stack,
                user, simulate=False):
    # ── validate ──
    for path in _as_list(rule.get('require')):
        value = _read(record, path)
        if value in (None, '', [], {}):
            _refuse(rule, f"{path} is required", index, ida, declared, result)
            return
    for path, pattern in (rule.get('match') or {}).items():
        value = _read(record, path)
        if value is None or not re.match(pattern, str(value)):
            _refuse(rule, f"{path} does not match {pattern}", index, ida, declared, result)
            return
    for path, bounds in (rule.get('range') or {}).items():
        value = _read(record, path)
        low, high = (bounds + [None, None])[:2] if isinstance(bounds, list) else (None, None)
        if value is None or (low is not None and value < low) or (high is not None and value > high):
            _refuse(rule, f"{path} is outside {low}–{high}", index, ida, declared, result)
            return

    # ── block ──
    if 'block' in rule:
        _refuse(rule, rule['block'], index, ida, declared, result, explicit=True)
        return

    # ── set ──
    for path, raw in (rule.get('set') or {}).items():
        if not _path_allowed(path, declared.get('may_set', [])):
            result.errors.append(f"{ida}: set '{path}' not allowed at this hook point")
            continue
        _write(record, path, _render(raw, ctx))
        result.set_fields.append(path)

    # ── create ──
    # A note is not a record: it is a line in the record's comments (Bill, 2026-09-24).
    if 'add_comment' in rule:
        spec = rule['add_comment']
        channel = _comment_channel(spec)
        if _path_allowed(f'comments.{channel}', declared.get('may_set', [])):
            if not simulate:
                text = spec.get('text', '') if isinstance(spec, dict) else spec
                _add_comment(record, channel, _render(text, ctx), ida, user)
            result.set_fields.append(f'comments.{channel}')
        else:
            result.errors.append(f"{ida}: add_comment — comments.{channel} is not settable here")
    if 'create_action' in rule:
        if 'action' in (declared.get('may_create') or []):
            if not simulate:
                _create_action(rule['create_action'], ctx, record, user)
            result.created.append('action')
        else:
            result.errors.append(f'{ida}: actions not allowed at this hook point')

    # ── log ──
    if 'append_log' in rule:
        spec = rule['append_log'] if isinstance(rule['append_log'], dict) else {'log': rule['append_log']}
        name = spec.get('log') or ''
        if name not in (declared.get('may_log') or []):
            result.errors.append(f"{ida}: log '{name}' not allowed at this hook point")
        else:
            line = {k: _render(v, ctx) for k, v in spec.items() if k != 'log'}
            line.setdefault('report', ida)
            if record is not None:
                line.setdefault('record', f'{record.__class__.__name__.lower()}:{getattr(record, "id", "")}')
            _append_log(name, line, simulate)
            result.logged.append(name)

    # ── chain ──
    if 'run_report' in rule:
        _run_report(rule['run_report'], report, ida, declared, ctx, result, depth, stack, user,
                    record, simulate)

    result.ran.append(f'{index}')


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _refuse(rule, message, index, ida, declared, result, explicit=False):
    """A failed validation stops the save when the point may block; otherwise it
    is recorded. Silence is never an option — one of the two always happens."""
    text = _render(rule.get('message') or message, {})
    if declared.get('may_block'):
        raise HookBlocked(text, rule_index=index, report_ida=ida)
    result.errors.append(f'{ida}: {text}')


def _comment_channel(spec) -> str:
    return (spec.get('channel') if isinstance(spec, dict) else None) or 'process'


def _add_comment(record, channel, text, ida, user):
    """A hook's comment carries the same stamp as one a person types (CommentsPanel):
    ``{user, mgs, time, user_id}`` in ``comments.<channel>``. The person is whoever's
    verb ran the hook; ``source`` names the hook."""
    from apps.core.services.comment_stamp import append_comment
    append_comment(record, channel, text, user=user, source=f'hook:{ida}')


def _create_action(spec, ctx, record, user):
    """A hook's action is written through the save door, as the system: authorized as our
    own code, with the action's own hooks (verbs.py refuses a chain deeper than one)."""
    from apps.core.models import Action
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    fields = {k: _render(v, ctx) for k, v in (spec or {}).items()}
    payload = {k: v for k, v in fields.items() if hasattr(Action, k)}
    if record is not None:
        payload['refs'] = {**(payload.get('refs') or {}), 'source': {
            'model': record.__class__.__name__.lower(), 'id': getattr(record, 'id', None)}}
    return save_record(Actor.system(source='hook'), payload, model_key='action').obj


def _run_report(target_ida, report, ida, declared, ctx, result, depth, stack, user, record,
                simulate=False):
    may_run = declared.get('may_run') or []
    if target_ida not in may_run and '*' not in may_run:
        result.errors.append(f"{ida}: may not call report '{target_ida}'")
        return
    if depth + 1 > MAX_CHAIN_DEPTH:
        result.errors.append(f'{ida}: chain deeper than {MAX_CHAIN_DEPTH} — refused at {target_ida}')
        return
    if target_ida in stack or target_ida == ida:
        cycle = ' → '.join(stack + [ida, target_ida])
        result.errors.append(f'{ida}: report cycle refused ({cycle})')
        return

    from apps.core.models import Report
    target = Report.objects.filter(ida=target_ida, is_active=True).first()
    if not target:
        result.errors.append(f"{ida}: report '{target_ida}' not found")
        return

    nested = run_phase(target, 'after', record=record, context=ctx,
                       depth=depth + 1, stack=stack + [ida], user=user, simulate=simulate)
    result.called.append(target_ida)
    result.errors += nested.errors
    result.set_fields += nested.set_fields
    result.created += nested.created
    result.logged += nested.logged


def _append_log(name: str, line: dict, simulate: bool = False) -> None:
    """Append one JSON line to a named hook log.

    The name is the whole address — no paths, no traversal. Logs land in
    BASE_DIR/logs/hooks/<name>.jsonl, and the registry decides which names a hook
    point may write.
    """
    if simulate:
        return
    import pathlib
    from datetime import datetime, timezone
    from django.conf import settings as django_settings

    folder = pathlib.Path(getattr(django_settings, 'BASE_DIR', '.')) / 'logs' / 'hooks'
    folder.mkdir(parents=True, exist_ok=True)
    entry = {'dt_utc': datetime.now(timezone.utc).isoformat(), **line}
    with open(folder / f'{name}.jsonl', 'a') as handle:
        handle.write(json.dumps(entry, default=str) + '\n')


def dry_run(hooks: dict, model_key: str = '', phase: str = 'after', record=None) -> dict:
    """Run a hook payload against a record without changing anything.

    This is the test function WCHQ uses to see what a submitted hook would do, and
    what a superuser can run before submitting. Writes are simulated: nothing is
    saved, no action is created, no log line is written.
    """
    from apps.core.models import Report
    problems = validate_hooks(hooks)
    if problems:
        return {'ok': False, 'problems': problems}

    if record is None and model_key:
        from apps.core.constants.model_registry import get_model
        model = get_model(model_key)
        if model is None:
            return {'ok': False, 'problems': [f"unknown model '{model_key}'"]}
        record = model()  # unsaved, empty — shows what the rules reach for

    probe = Report(ida='dry-run', name='dry run', config={'hooks': hooks})
    blocked = ''
    try:
        result = run_phase(probe, phase, record=record, changed=set(), simulate=True)
    except HookBlocked as stop:
        blocked = stop.message
        result = HookResult()

    return {
        'ok': not result.errors and not blocked,
        'blocked': blocked,
        'would_set': sorted(set(result.set_fields)),
        'would_create': sorted(set(result.created)),
        'would_log': sorted(set(result.logged)),
        'would_call': sorted(set(result.called)),
        'problems': result.errors,
    }


def _mark_unhealthy(report, reason):
    """A hook that runs over budget says so on its own record. Three strikes and
    it stops running until a superuser looks at it."""
    try:
        from django.utils import timezone
        meta = report.metadata if isinstance(report.metadata, dict) else {}
        health = meta.get('hook_health') or {}
        health['strikes'] = int(health.get('strikes') or 0) + 1
        health['last_reason'] = reason
        health['last_utc'] = timezone.now().isoformat()
        if health['strikes'] >= 3:
            health['suspended'] = True
        meta['hook_health'] = health
        report.metadata = meta
        report.save(update_fields=['metadata', 'dt_modified'])
    except Exception:
        logger.exception('[HOOK] could not record hook health')


# ── model save points ────────────────────────────────────────────────────────

def hooks_for_point(point: str):
    """Active reports whose hooks attach to this point, oldest first.

    A point is a slot: one report per slot (Bill, 2026-09-24). The Report save gate
    refuses a second, so more than one here is a fault the verb refuses loudly.
    Suspended hooks (three budget strikes) are skipped until a superuser clears the
    strike count.
    """
    from apps.core.models import Report
    candidates = Report.objects.filter(
        is_active=True, config__hooks__point=point
    ).order_by('pk')
    ready = []
    for report in candidates:
        health = (report.metadata or {}).get('hook_health') or {}
        if health.get('suspended'):
            logger.warning('[HOOK] %s suspended — skipped at %s', report.ida, point)
            continue
        ready.append(report)
    return ready


class HookSlotConflict(Exception):
    """Two active reports claim one slot. Carries their idas."""

    def __init__(self, point: str, idas: List[str]):
        super().__init__(f"{len(idas)} reports claim the hook slot {point}: {', '.join(idas)}")
        self.point = point
        self.idas = idas


def slot_point(model_key: str, verb: str, moment: str) -> str:
    """The slot a user hook fills: ``<model>.<verb>_<pre|post>`` (WC2's ``OnSave_<Table>``)."""
    return f'{model_key}.{verb}_{moment}'


def run_hooks(model_key: str, verb: str, moment: str, record, changed=None,
              user=None) -> HookResult:
    """Run the one report in the slot ``<model>.<verb>_<moment>`` for one record.

    moment is 'pre' or 'post'. A pre rule that blocks raises HookBlocked; two reports in
    one slot raise HookSlotConflict. Nothing here opens a dialog or waits on a network call.
    """
    point = slot_point(model_key, verb, moment)
    reports = hooks_for_point(point)
    if not reports:
        return HookResult()
    if len(reports) > 1:
        raise HookSlotConflict(point, [r.ida for r in reports])
    return run_phase(
        reports[0], 'before' if moment == 'pre' else 'after', record=record,
        changed=changed, context={'phase': f'{verb}_{moment}', 'model': model_key,
                                  'verb': verb}, user=user,
        budget_key=f'{verb}_{moment}',
    )


# ── WCHQ review and Athena binding ───────────────────────────────────────────
#
# A hook is confirmed by WCHQ, not by the instance that wrote it. WCHQ reviews the
# payload and returns a token that binds one exact payload to one instance:
#
#     token = HMAC-SHA256(key=athena_token, msg=f'{instance_uuid}:{hook_hash}')
#
# The shared athena_token lives on the wchq-conn-upstream Connection, the same
# secret the instance-submit endpoint already trusts. Verification is local, so a
# confirmed hook keeps running when WCHQ is unreachable, and a payload that
# changes by one character stops running until it is confirmed again.



def _instance_uuid() -> str:
    from decouple import config
    return config('WC_INSTANCE_UUID', default='')


ISSUER_WCHQ = 'wchq'
ISSUER_ATHENA = 'athena'


def expected_token(payload_hash: str, issuer: str = ISSUER_WCHQ) -> str:
    """The token this issuer should have produced for this payload on this instance.

    WCHQ signs with the shared Athena token on the upstream Connection. The local
    Athena signs with a key derived from SECRET_KEY, which never leaves the box —
    so a locally cleared hook is cleared here and nowhere else, and cannot be
    carried to another installation.
    """
    import hmac
    if issuer == ISSUER_ATHENA:
        from django.conf import settings as django_settings
        secret = f'athena-hook:{django_settings.SECRET_KEY}'
    else:
        from apps.sync.services.connections import wchq_link
        secret = wchq_link()[1]
    if not secret:
        return ''
    message = f'{issuer}:{_instance_uuid()}:{payload_hash}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def token_valid(report) -> bool:
    import hmac
    state = athena_state(report)
    if not state.get('token') or not state['hash_matches']:
        return False
    expected = expected_token(state['hash_now'], state.get('issuer') or ISSUER_WCHQ)
    return bool(expected) and hmac.compare_digest(expected, state['token'])


def submit_for_review(report, note: str = '') -> dict:
    """Send a hook to WCHQ for confirmation. Alice owns the exchange — see
    apps/ai_assistant/services/hook_review.py for the four-message protocol and
    the state she keeps on the report."""
    from apps.ai_assistant.services.hook_review import send_review_request
    return send_review_request(report, note=note)


def apply_clearance(report, token: str, issuer: str = ISSUER_WCHQ, **extra) -> dict:
    """Store a clearance token, but only if it verifies against this payload here."""
    hooks = dict((report.config or {}).get('hooks') or {})
    payload_hash = hook_hash(hooks)
    expected = expected_token(payload_hash, issuer)
    if not expected:
        return {'status': 'error', 'problems': [f'no signing key for issuer {issuer}']}

    import hmac
    if not hmac.compare_digest(expected, token):
        return {'status': 'error', 'problems': ['token does not match this payload on this instance']}

    athena = dict(hooks.get('athena') or {})
    athena.update({'required': True, 'cleared': True, 'token': token, 'hash': payload_hash,
                   'issuer': issuer, **extra})
    hooks['athena'] = athena
    report.config = {**(report.config or {}), 'hooks': hooks}
    report._hooks_authorized = True
    report.save(update_fields=['config', 'dt_modified'])
    return {'status': 'cleared', 'hash': payload_hash, 'issuer': issuer}


def apply_clearance_bundle(payload: dict) -> dict:
    """A WCHQ message applied from a shell or a carried file. One path: Alice's."""
    from apps.ai_assistant.services.hook_review import receive
    return receive(payload)
