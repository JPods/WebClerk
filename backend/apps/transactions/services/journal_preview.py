"""The journal entry a document makes — before it posts, and after (Bill, 2026-10-27).

POST /wcapi/<invoice|cash|receipt>/<id>/journal_preview/

The flight simulator teaches double entry: an invoice, its cash and a receipt each become a
journal entry, every line an account debited or credited with its $. A teaching tool, not an
accounting one — so the preview is never a second copy of the posting rules: it runs the real
journalize for the document inside a transaction, reads the GL rows that wrote, and rolls the
transaction back. What the preview shows is what Post (the journalize command) will write.
A document already posted shows the rows that stand (a reversed pair is not standing).

Answer: {posted, entries: [{account, name, debit, credit, purpose}], debits, credits,
balanced, note}. note says why there is nothing to post (on hold, already posted, nothing
received), in the poster's own words.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction

#: The documents the console journalizes, and the poster each one uses.
JOURNAL_MODELS = ('invoice', 'cash', 'receipt')


def poster(model_key: str):
    from apps.accounts.services import journalize as posting
    return {'invoice': posting.journalize_invoice, 'cash': posting.journalize_cash,
            'receipt': posting.journalize_receipt}[model_key]


def _entries(rows) -> List[Dict[str, Any]]:
    from apps.accounts.models import GlAccount
    names = dict(GlAccount.objects.filter(ida__in={r.account for r in rows}).values_list('ida', 'name'))
    return [{'account': r.account, 'name': names.get(r.account, r.account),
             'debit': float(r.debit or 0), 'credit': float(r.credit or 0), 'purpose': r.purpose or ''}
            for r in rows]


def _standing(model_key: str, pk: int):
    """The rows this document posted that still stand: not a reversal, not reversed."""
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_model=model_key, source_id=pk)
    reversed_ids = set(rows.exclude(reversal_of__isnull=True).values_list('reversal_of', flat=True))
    return [r for r in rows.filter(reversal_of__isnull=True).order_by('pk') if r.pk not in reversed_ids]


def journal_preview(ctx) -> Dict[str, Any]:
    from apps.accounts.models import GlJournal
    model_key, pk = ctx.model_key, ctx.obj.pk
    standing = _standing(model_key, pk)
    if standing:
        entries, posted, note = _entries(standing), True, ''
    else:
        posted = False
        try:
            with transaction.atomic():
                last = GlJournal.objects.order_by('-pk').values_list('pk', flat=True).first() or 0
                result = poster(model_key)(pk)
                entries = _entries(list(GlJournal.objects.filter(pk__gt=last).order_by('pk')))
                transaction.set_rollback(True)      # a preview writes nothing
        except Exception as e:                      # noqa: BLE001 — what Post would refuse with
            result, entries = {'error': str(e)}, []
        note = '' if entries else (result.get('error') or result.get('status') or 'Nothing to post.')
    debits = sum((Decimal(str(e['debit'])) for e in entries), Decimal('0'))
    credits = sum((Decimal(str(e['credit'])) for e in entries), Decimal('0'))
    return {'posted': posted, 'entries': entries, 'debits': float(debits), 'credits': float(credits),
            'balanced': debits == credits, 'note': note}


def register() -> None:
    from apps.core.services.verbs import register_command
    for model_key in JOURNAL_MODELS:
        register_command(model_key, 'journal_preview', journal_preview)
