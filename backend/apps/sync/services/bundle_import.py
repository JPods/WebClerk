"""Import on one route (plan §17; Bill, 2026-09-26, §17.12–13).

    POST /wcapi/bundle/<id>/preview/   Alice's pre-import: a real run through the door, rolled back
    POST /wcapi/bundle/<id>/approve/   Alice, then Athena — each pinned to the content hash
    POST /wcapi/bundle/<id>/import/    a superuser applies every row through the door, all or nothing

The data is cleaned outside WebClerk (with AI, DynamicCatalogs, other services); WebClerk parses
no file. A bundle's payload is ``{"records": [{"model_name": "...", "uuid": "...", ...fields,
"lines": [...]}, ...]}``. Every row carries a uuid: one WebClerk knows is an update; an unknown
one is a new record that keeps it, with id and ida assigned (save_record, _by_uuid). Nothing is
ever matched on name or SKU at load — the pre-import shows look-alikes (with their id, ida and
uuid) so the person cleans the data up first.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.conf import settings
from django.db import transaction

from apps.core.services.door import Refused

#: Fields a row may not carry unless a superuser means it (Athena checks them).
AUTHORITY_FIELDS = ('role', 'is_staff', 'is_superuser', 'security_level', 'user_permissions', 'groups')
#: Where a look-alike is sought, per model: the fields that make two records "the same thing".
LOOK_ALIKE_FIELDS = {
    'item': ('sku', 'name'),
    'contact': ('email',),
    'orgbase': ('company', 'email'), 'customer': ('company', 'email'), 'vendor': ('company', 'email'),
    'manufacturer': ('company',), 'rep': ('company',), 'employee': ('company',),
    'email': ('email',), 'phone': ('number',), 'warehouse': ('code', 'name'),
}
AGENTS = {'alice': 'ALICE_WC_EMAIL', 'athena': 'ATHENA_WC_EMAIL'}


def _now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _records(bundle) -> List[Dict[str, Any]]:
    payload = bundle.get_payload() if hasattr(bundle, 'get_payload') else None
    if payload is None:
        from apps.sync.services.bundle_storage import load_payload_by_path
        payload = load_payload_by_path((bundle.config or {}).get('payload_path') or '')
    rows = payload.get('records') if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise Refused(400, 'no_records', f'Bundle {bundle.pk} carries no records: '
                      f'{{"records": [{{"model_name": ..., "uuid": ..., ...}}]}}.', {})
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get('model_name') or not row.get('uuid'):
            raise Refused(400, 'row_incomplete', f'Row {i}: every row names its model_name and carries a '
                          f'uuid (Bill: a uuid that matches updates; one that does not is new).',
                          {'row': i})
        try:
            _uuid.UUID(str(row['uuid']))
        except ValueError:
            raise Refused(400, 'bad_uuid', f'Row {i}: "{row["uuid"]}" is not a uuid.', {'row': i})
    return rows


def content_hash(bundle, rows: List[Dict[str, Any]]) -> str:
    """SHA-256 of the canonical rows plus the connection: any change voids an approval."""
    canon = json.dumps({'connection': bundle.connection_id, 'records': rows},
                       sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def _sign(bundle, run: Dict[str, Any]) -> str:
    """The run is kept in bundle.config, which admins and agents can PUT; only a run this module
    signed counts (Fable: a hand-written approval would otherwise import unseen content)."""
    body = json.dumps({'bundle': bundle.pk, 'run': {k: v for k, v in run.items() if k != 'sig'}},
                      sort_keys=True, separators=(',', ':'), default=str)
    return hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()


def _run(bundle) -> Dict[str, Any]:
    run = dict((bundle.config or {}).get('import_run') or {})
    if run and not hmac.compare_digest(str(run.get('sig', '')), _sign(bundle, run)):
        run = {}                                # written by hand, not by the route: nothing stands
    run.setdefault('approvals', {})
    return run


def _store_run(bundle, run: Dict[str, Any]) -> None:
    run['sig'] = _sign(bundle, run)
    config = dict(bundle.config or {})
    config['import_run'] = run
    type(bundle).objects.filter(pk=bundle.pk).update(config=config)
    bundle.config = config


def _require_superuser(actor) -> None:
    user = getattr(actor, 'user', None)
    if not (user and getattr(user, 'is_superuser', False)):
        raise Refused(403, 'superuser_required', 'Importing is managed by a superuser (Bill, 2026-09-26). '
                      'An automatic import needs a signed-off Connection with a token.', {})


def _row_for_door(row: Dict[str, Any]) -> Dict[str, Any]:
    """The row as the door takes it: named by uuid, never by id; an exported version dropped
    (it would read as a stale edit), and the source's system stamps dropped: the door refuses
    them (Bill, 2026-09-28), and an imported record is created, modified and journalized here,
    by its own events. The bundle keeps the source's stamps."""
    from apps.core.services.dt_fields import SYSTEM_DT_FIELDS
    return {k: v for k, v in row.items() if k not in ('id', 'version') and k not in SYSTEM_DT_FIELDS}


def _look_alikes(model_key: str, row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Existing records that look like this new row, with their id, ida and uuid, so the person
    can put the right uuid on the row before import (Bill: Alice shows the overlap)."""
    from apps.core.services.door import resolve_model
    fields = LOOK_ALIKE_FIELDS.get(model_key)
    if not fields:
        return []
    model_cls, _, _ = resolve_model(model_key)
    names = {f.name for f in model_cls._meta.concrete_fields}
    found: Dict[int, Dict[str, Any]] = {}
    for field in fields:
        value = row.get(field)
        if field not in names or not isinstance(value, str) or not value.strip():
            continue
        for rec in model_cls.objects.filter(**{f'{field}__iexact': value.strip()}).exclude(uuid=row.get('uuid'))[:5]:
            found.setdefault(rec.pk, {'id': rec.pk, 'ida': getattr(rec, 'ida', None), 'uuid': str(rec.uuid),
                                      'matched_on': field})
    return list(found.values())


def preview(ctx) -> Dict[str, Any]:
    """Alice's pre-import: every row through the real door, then all of it rolled back."""
    from apps.core.models.pending import Pending
    from apps.core.services.door import resolve_model
    from apps.core.services.save import save_record
    _require_superuser(ctx.actor)
    bundle = ctx.obj
    rows = _records(bundle)
    results, services = [], {}
    # Look-alikes against the data as it stands, before any row of this bundle changes it.
    known_by_row, alikes_by_row = {}, {}
    for i, row in enumerate(rows):
        model_cls, model_key, _ = resolve_model(row['model_name'])
        known_by_row[i] = model_cls.objects.filter(uuid=row['uuid']).exists()
        if not known_by_row[i]:
            alikes_by_row[i] = _look_alikes(model_key, row)
    sid = transaction.savepoint()
    try:
        for i, row in enumerate(rows):
            model_cls, model_key, _ = resolve_model(row['model_name'])
            known = known_by_row[i]
            entry: Dict[str, Any] = {'row': i, 'model': model_key, 'uuid': str(row['uuid']),
                                     'action': 'update' if known else 'new'}
            if alikes_by_row.get(i):
                entry['look_alikes'] = alikes_by_row[i]
            before = Pending.objects.order_by('-pk').values_list('pk', flat=True).first() or 0
            try:
                with transaction.atomic():
                    result = save_record(ctx.actor, _row_for_door(row))
                if known:                       # a new row's previewed id is not the id it will get
                    entry['id'] = result.obj_id
                if result.messages:
                    entry['messages'] = list(result.messages)
            except Refused as e:
                entry.update({'action': 'refused', 'code': e.code, 'reason': e.message})
            written = (Pending.objects.filter(pk__gt=before).values_list('purpose', flat=True))
            for purpose in written:
                entry.setdefault('services', {}).setdefault(purpose or 'pending', 0)
                entry['services'][purpose or 'pending'] += 1
                services[purpose or 'pending'] = services.get(purpose or 'pending', 0) + 1
            results.append(entry)
    finally:
        transaction.savepoint_rollback(sid)     # nothing the preview did stays
    summary = {'rows': len(rows),
               'new': sum(1 for r in results if r['action'] == 'new'),
               'update': sum(1 for r in results if r['action'] == 'update'),
               'refused': sum(1 for r in results if r['action'] == 'refused'),
               'look_alike_rows': sum(1 for r in results if r.get('look_alikes')),
               'services': services}
    run = _run(bundle)
    run.update({'content_hash': content_hash(bundle, rows), 'approvals': {},
                'preview': {'dt': _now(), 'summary': summary, 'rows': results}})
    _store_run(bundle, run)
    return {'summary': summary, 'rows': results, 'content_hash': run['content_hash']}


def approve(ctx) -> Dict[str, Any]:
    """Alice or Athena signs the content the preview saw — identified by their login, never by
    a field in the request."""
    bundle = ctx.obj
    user = getattr(ctx.actor, 'user', None)
    email = (getattr(user, 'email', '') or '').lower()
    who = next((name for name, key in AGENTS.items()
                if getattr(settings, key, '') and email == getattr(settings, key, '').lower()), None)
    if who is None or not is_approver(ctx.actor):
        raise Refused(403, 'approver_required', 'An import is approved by Alice and by Athena, each from '
                      'their own login.', {})
    rows = _records(bundle)
    run = _run(bundle)
    current = content_hash(bundle, rows)
    if not run.get('preview') or run.get('content_hash') != current:
        raise Refused(409, 'preview_required', 'Run the pre-import on this content first '
                      '(POST /wcapi/bundle/<id>/preview/).', {})
    summary = (run['preview'] or {}).get('summary') or {}
    notes: List[str] = []
    if summary.get('refused'):
        raise Refused(409, 'preview_refusals', f'{summary["refused"]} row(s) were refused in the pre-import; '
                      f'clean them up first.', {'refused': summary['refused']})
    if who == 'alice' and summary.get('look_alike_rows'):
        raise Refused(409, 'look_alikes', f'{summary["look_alike_rows"]} new row(s) look like existing '
                      f'records; put the existing uuid on each row, or confirm they are new, and preview '
                      f'again.', {'look_alike_rows': summary['look_alike_rows']})
    if who == 'athena':
        carrying = sorted({f for row in rows for f in AUTHORITY_FIELDS if f in row})
        if carrying:
            raise Refused(409, 'authority_fields', f'Rows carry authority fields ({", ".join(carrying)}); '
                          f'these are set by a person in WebClerk, never by an import.', {'fields': carrying})
        notes.append(f"services: {summary.get('services') or {}}")
    run['approvals'][who] = {'by': email, 'by_id': getattr(user, 'pk', None), 'dt': _now(),
                             'content_hash': current, 'notes': notes}
    _store_run(bundle, run)
    return {'approved_by': who, 'content_hash': current,
            'waiting_for': [n for n in AGENTS if n not in run['approvals']]}


def run_import(ctx) -> Dict[str, Any]:
    """A superuser applies every row through the door, all or nothing, once Alice and Athena
    have approved exactly this content."""
    from apps.core.services.save import save_record
    _require_superuser(ctx.actor)
    bundle = ctx.obj
    rows = _records(bundle)
    run = _run(bundle)
    current = content_hash(bundle, rows)
    missing = [n for n in AGENTS if (run['approvals'].get(n) or {}).get('content_hash') != current]
    if missing:
        raise Refused(409, 'approval_required', f'Waiting for {" and ".join(missing)} to approve this content '
                      f'(an approval of different content does not count).', {'waiting_for': missing})
    created = updated = 0
    for i, row in enumerate(rows):
        try:
            result = save_record(ctx.actor, _row_for_door(row))
        except Refused as e:                    # all or nothing: the command's transaction unwinds
            raise Refused(e.status, e.code, f'Row {i} ({row["model_name"]} {row["uuid"]}): {e.message} '
                          f'Nothing was imported.', {'row': i, 'details': e.details})
        created += 1 if result.created else 0
        updated += 0 if result.created else 1
    run['imported'] = {'dt': _now(), 'by': getattr(getattr(ctx.actor, 'user', None), 'email', ''),
                       'created': created, 'updated': updated, 'content_hash': current}
    _store_run(bundle, run)
    type(bundle).objects.filter(pk=bundle.pk).update(status='success')
    return {'created': created, 'updated': updated}


def write_digest(day: str | None = None) -> Dict[str, Any]:
    """Nightly: the day's imports (hash, approvals, who imported) written outside the database,
    one JSON line per bundle, to the work folder imports/digest, whose manifest backup rule is
    offsite (Allie's plan, Bill 2026-09-26; review 2027-02). Rewriting a day's file is harmless —
    it is rebuilt from the bundles."""
    from datetime import timedelta
    from common.work_folders import work_folder
    from apps.sync.models import Bundle
    day = day or (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
    lines = []
    for b in (Bundle.objects.filter(config__import_run__imported__dt__startswith=day)
              .order_by('pk').only('pk', 'connection_id', 'config')):
        run = _run(b)
        if not run.get('imported'):             # unsigned or hand-edited: not an import
            continue
        lines.append(json.dumps({
            'bundle': b.pk, 'connection': b.connection_id, 'content_hash': run.get('content_hash'),
            'approvals': {n: {k: a.get(k) for k in ('by', 'dt', 'content_hash')}
                          for n, a in (run.get('approvals') or {}).items()},
            'imported': run['imported'], 'sig': run.get('sig')}, sort_keys=True))
    if not lines:
        return {'day': day, 'imports': 0}
    out = work_folder('imports/digest')
    (out / f'{day}.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'day': day, 'imports': len(lines), 'path': str(out / f'{day}.jsonl')}


def is_approver(actor) -> bool:
    """Alice's or Athena's own login (by the configured email), not acting as anyone."""
    user = getattr(actor, 'user', None)
    email = (getattr(user, 'email', '') or '').lower()
    # An agent login, not a person who set their email to the agent's (Fable).
    return (not getattr(actor, 'acting_as', None) and bool(email)
            and getattr(user, 'role', '') == 'agent' and getattr(user, 'is_active', False)
            and any(email == (getattr(settings, key, '') or '').lower() for key in AGENTS.values()))


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('bundle', 'preview', preview)
    # The approvers reach the staff-only bundle for this one command, and only this one.
    register_command('bundle', 'approve', approve, admit=is_approver)
    register_command('bundle', 'import', run_import)
