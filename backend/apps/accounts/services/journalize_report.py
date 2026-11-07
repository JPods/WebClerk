"""The Journalize reports — one per model that posts to the GL (Bill, 2026-11-07: "There should be
a user report to journalize documents. It should not be automatic." "We should have a report for
every model that displays unjournalized records. The users then choose the records they want
journalized and post them."). The batch (batch_journalize) is gone.

One generator, one Report record per model (report_registry.SHIPPED_REPORTS, key
``journalize_<model>``, screen ``/journalize/<model>``). The report lists the model's unposted
records — a zz/qq row never — each either ready, with the entry it will post (the real posting,
rolled back: journal_preview.preview_for), or waiting, with the reason in the door's or the
poster's own words. The person ticks the ready rows and posts: every row goes through the door
command ``journalize`` on its own, so one refusal stops nothing else, and the run answers
posted/refused per row. A JournalBatch is the run's audit record.

Models that write GL rows without a journalize command, and so have no report: a commission
accrues with its invoice (commission_compute, inside journalize_invoice), a rebate accrues by the
manage action accrue_manufacturer_rebate, a reversal is unjournalize's (ledger_balance), an
inventory adjustment posts through its workorder (journalize_adjustment has no caller).
"""
from __future__ import annotations

from typing import Any, Dict, List

from django.apps import apps as dj_apps

#: every model with a journalize command (journal_commands.register), in the order the sidebar shows
POSTING_MODELS = ('invoice', 'cash', 'receipt', 'workorder')
_MODELS = {'invoice': ('transactions', 'Invoice'), 'cash': ('transactions', 'Cash'),
           'receipt': ('transactions', 'Receipt'), 'workorder': ('transactions', 'WorkOrder')}
LABELS = {'invoice': 'Journalize invoices', 'cash': 'Journalize cash',
          'receipt': 'Journalize receipts', 'workorder': 'Journalize workorders'}


def _model(model_key: str):
    if model_key not in _MODELS:
        raise ValueError(f'No journalize report for {model_key!r}; one exists for {", ".join(POSTING_MODELS)}')
    return dj_apps.get_model(*_MODELS[model_key])


def waiting(obj, model_key: str) -> str:
    """Why the door would refuse to post ``obj`` — incomplete, or an invoice not yet released — in
    the command's own words (journal_commands.journalize uses the same two checks); '' otherwise.
    What the poster itself would refuse (nothing received, on hold) comes from the preview."""
    from apps.transactions.services import validate_status
    missing = validate_status.incomplete(obj, model_key)
    if missing:
        return validate_status.incomplete_coaching(model_key, 'journalize', missing)
    if not validate_status.may_post(obj, model_key):
        return validate_status.not_released_coaching(model_key, obj.status)
    return ''


def _party(obj) -> str:
    for name in ('customer', 'vendor'):
        org = getattr(obj, name, None)
        if org is not None:
            return getattr(org, 'company', '') or ''
    return ''


def _total(obj):
    if hasattr(obj, 'amount') and not hasattr(obj, 'totals'):
        return float(obj.amount or 0)
    total = (getattr(obj, 'totals', None) or {}).get('total')
    return float(total) if total not in (None, '') else None


def unposted(model_key: str, limit: int = 200) -> Dict[str, Any]:
    """The model's unposted records, oldest first, each ready (with its preview) or waiting (with
    its reason). ``total`` counts them all; ``rows`` carries the first ``limit``."""
    from apps.core.services.tally import tallied
    from apps.transactions.services.journal_preview import preview_for
    Model = _model(model_key)
    qs = tallied(Model.objects.filter(dt_journaled=0, is_active=True)).order_by('dt_created', 'pk')
    rows: List[Dict[str, Any]] = []
    for obj in qs[:limit]:
        why, preview = waiting(obj, model_key), None
        if not why:
            preview = preview_for(model_key, obj.pk)
            if not preview['entries']:
                why = preview['note'] or 'Nothing to post.'
        rows.append({'id': obj.pk, 'ida': obj.ida, 'status': obj.status or '', 'party': _party(obj),
                     'total': _total(obj), 'dt_created': obj.dt_created, 'waiting': why,
                     'preview': preview if not why else None})
    ready = sum(1 for r in rows if not r['waiting'])
    return {'model': model_key, 'rows': rows, 'ready': ready, 'waiting': len(rows) - ready,
            'total': qs.count(), 'limit': limit}


def executor(model_key: str):
    """The report registry's executor for this model's report."""
    def run(params: Dict[str, Any]) -> Dict[str, Any]:
        return unposted(model_key, int((params or {}).get('limit') or 200))
    return run


def post_selected(actor, model_key: str, ids) -> Dict[str, Any]:
    """Post the ticked rows, each through the door command on its own; answer per row. The run is
    recorded as a JournalBatch (its audit record): counts, who, when, and every row's answer."""
    from apps.core.services.door import Refused
    from apps.core.services.verbs import run_command
    from apps.accounts.services.journalize import _now_ms
    Model = _model(model_key)
    JournalBatch = dj_apps.get_model('accounts', 'JournalBatch')
    ids = [int(i) for i in (ids or [])]
    started = _now_ms()
    batch = JournalBatch.objects.create(
        ida=f'JB-{model_key}-{started}', batch_type=model_key, status=JournalBatch.STATUS_PROCESSING,
        dt_started=started, run_by=getattr(actor, 'user', None), config={'model': model_key, 'ids': ids})
    posted, refused = [], []
    for pk in ids:
        obj = Model.objects.filter(pk=pk).first()
        row = {'id': pk, 'ida': getattr(obj, 'ida', '') or ''}
        if obj is None:
            refused.append({**row, 'code': 'not_found', 'message': f'{model_key} {pk} does not exist.'})
            continue
        try:
            result = run_command(actor, 'journalize', model_key, pk, {})
            posted.append({**row, 'created': int((result or {}).get('created') or 0)})
        except Refused as e:                       # this row's own refusal; the next row still runs
            refused.append({**row, 'code': e.code, 'message': e.message})
    batch.count_posted, batch.count_exceptions = len(posted), len(refused)
    batch.status = JournalBatch.STATUS_HAS_EXCEPTIONS if refused else JournalBatch.STATUS_COMPLETE
    batch.dt_completed = _now_ms()
    batch.config = {'model': model_key, 'ids': ids, 'posted': posted, 'refused': refused}
    batch.save(update_fields=['count_posted', 'count_exceptions', 'status', 'dt_completed', 'config',
                              'dt_modified', 'version'])
    return {'model': model_key, 'posted': posted, 'refused': refused, 'batch': batch.ida}
