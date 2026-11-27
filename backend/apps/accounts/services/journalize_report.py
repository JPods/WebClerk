"""The Journalize reports — one per model that posts to the GL (Bill, 2026-11-07: "There should be
a user report to journalize documents. It should not be automatic." "We should have a report for
every model that displays unjournalized records. The users then choose the records they want
journalized and post them."). The batch (batch_journalize) is gone.

One generator, one Report record per model (report_registry.SHIPPED_REPORTS, key
``journalize_<model>``, screen ``/journalize/<model>``). The report lists the model's unposted
records, each either ready, with the entry it will post (the real posting,
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

from typing import Any, Dict, List, Optional

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
    """Why the door would refuse to post ``obj`` — incomplete, or an invoice on hold — in the
    command's own words (journal_commands.journalize uses the same two checks); '' otherwise. A
    planned invoice is postable: the post releases it (note()). What the poster itself would
    refuse (nothing received, on hold) comes from the preview."""
    from apps.transactions.services import validate_status
    missing = validate_status.incomplete(obj, model_key)
    if missing:
        return validate_status.incomplete_coaching(model_key, 'journalize', missing)
    if not validate_status.may_post(obj, model_key) and not validate_status.releases_on_post(obj, model_key):
        return validate_status.not_released_coaching(model_key, obj.status)
    return ''


def note(obj, model_key: str) -> str:
    """What posting this ready row also does — releases a planned invoice (Bill, 2026-11-08)."""
    from apps.transactions.services import validate_status
    if validate_status.releases_on_post(obj, model_key):
        return validate_status.release_on_post_note(model_key, obj.status)
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


#: The note on a ready row whose posting writes no GL row: a zero cash, a workorder whose work
#: carried no value. Posting stamps it journalized (FAULT 2026-11-27: these sat "waiting" for good).
COMPLETES_NOTE = 'completes with no GL entry'


def unposted(model_key: str, limit: int = 200, begin: Optional[int] = None,
             end: Optional[int] = None) -> Dict[str, Any]:
    """The model's unposted records, oldest first, each ready (with its preview) or waiting (with
    its reason). ``total`` counts them all; ``rows`` carries the first ``limit``. ``begin`` and
    ``end`` (UTC epoch ms, inclusive) choose by dt_created, the date the report shows: a week at a
    time (Bill, 2026-11-27: journalize at least weekly). They choose rows; they do not date the GL."""
    from apps.accounts.services.journalize import COMPLETES_STATUSES
    from apps.transactions.services.journal_preview import preview_for
    Model = _model(model_key)
    qs = Model.objects.filter(dt_journaled=0, is_active=True)
    if begin is not None:
        qs = qs.filter(dt_created__gte=int(begin))
    if end is not None:
        qs = qs.filter(dt_created__lte=int(end))
    qs = qs.order_by('dt_created', 'pk')
    rows: List[Dict[str, Any]] = []
    for obj in qs[:limit]:
        why, preview, completes = waiting(obj, model_key), None, False
        if not why:
            preview = preview_for(model_key, obj.pk)
            if not preview['entries']:
                completes = preview['note'] in COMPLETES_STATUSES
                why = '' if completes else (preview['note'] or 'Nothing to post.')
        row_note = COMPLETES_NOTE if completes else (note(obj, model_key) if not why else '')
        row = {'id': obj.pk, 'ida': obj.ida, 'status': obj.status or '', 'party': _party(obj),
               'total': _total(obj), 'dt_created': obj.dt_created, 'waiting': why,
               'note': row_note, 'preview': preview if not why else None}
        if not why and preview and preview.get('unallocated'):
            # Charges no line carries: the person ticks post_unallocated for this row, or it is
            # refused on Post with the amounts (journal_commands). Never ticked by default.
            row['unallocated'] = preview['unallocated']
        rows.append(row)
    ready = sum(1 for r in rows if not r['waiting'])
    return {'model': model_key, 'rows': rows, 'ready': ready, 'waiting': len(rows) - ready,
            'total': qs.count(), 'limit': limit, 'begin': begin, 'end': end}


def executor(model_key: str):
    """The report registry's executor for this model's report."""
    def run(params: Dict[str, Any]) -> Dict[str, Any]:
        params = params or {}
        bound = lambda key: int(params[key]) if params.get(key) not in (None, '') else None  # noqa: E731
        return unposted(model_key, int(params.get('limit') or 200), bound('begin'), bound('end'))
    return run


def post_selected(actor, model_key: str, ids, options=None) -> Dict[str, Any]:
    """Post the ticked rows, each through the door command on its own; answer per row. The run is
    recorded as a JournalBatch (its audit record): counts, who, when, and every row's answer.
    ``options`` carries a row's own choices by its id, {"<id>": {"post_unallocated": true}}, sent to
    that row's command only (a receipt's unallocated charges, ticked by the person)."""
    from apps.core.services.door import Refused
    from apps.core.services.verbs import run_command
    from apps.accounts.services.journalize import _now_ms
    Model = _model(model_key)
    JournalBatch = dj_apps.get_model('accounts', 'JournalBatch')
    ids = [int(i) for i in (ids or [])]
    options = {int(k): dict(v) for k, v in (options or {}).items() if isinstance(v, dict)}
    started = _now_ms()
    batch = JournalBatch.objects.create(
        ida=f'JB-{model_key}-{started}', batch_type=model_key, status=JournalBatch.STATUS_PROCESSING,
        dt_started=started, run_by=getattr(actor, 'user', None), config={'model': model_key, 'ids': ids})
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    posted, refused = [], []
    for pk in ids:
        obj = Model.objects.filter(pk=pk).first()
        row = {'id': pk, 'ida': getattr(obj, 'ida', '') or ''}
        if obj is None:
            refused.append({**row, 'code': 'not_found', 'message': f'{model_key} {pk} does not exist.'})
            continue
        try:
            before = GlJournal.objects.order_by('-pk').values_list('pk', flat=True).first() or 0
            result = run_command(actor, 'journalize', model_key, pk,
                                 {'post_unallocated': True} if options.get(pk, {}).get('post_unallocated') else {})
            # The rows this record's post wrote name the run that posted them (the lead, 2026-11-27):
            # its own rows only, by its source and above where the run began.
            GlJournal.objects.filter(pk__gt=before, source_model=model_key, source_id=pk,
                                     batch_id='').update(batch_id=batch.ida)
            posted.append({**row, 'created': int((result or {}).get('created') or 0),
                           'messages': list((result or {}).get('messages') or [])})
        except Refused as e:                       # this row's own refusal; the next row still runs
            refused.append({**row, 'code': e.code, 'message': e.message})
    batch.count_posted, batch.count_exceptions = len(posted), len(refused)
    batch.status = JournalBatch.STATUS_HAS_EXCEPTIONS if refused else JournalBatch.STATUS_COMPLETE
    batch.dt_completed = _now_ms()
    batch.config = {'model': model_key, 'ids': ids, 'posted': posted, 'refused': refused,
                    'options': {str(k): v for k, v in options.items()}}
    batch.save(update_fields=['count_posted', 'count_exceptions', 'status', 'dt_completed', 'config',
                              'dt_modified', 'version'])
    return {'model': model_key, 'posted': posted, 'refused': refused, 'batch': batch.ida}
