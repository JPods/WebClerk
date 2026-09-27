"""Unjournalize: a command on the record, kept and made glaring (Bill, 2026-09-26).

"We will force the users to make amending documents … Users will frequently unjournalize
records, correct things, then rerun journals. My preference is they do not. They should find the
defects [and] create an adjustment document so the fault becomes glaring, and hopefully later
preventable." And: "Keep the capacity to unjournalize."

So a journalized record refuses change and coaches toward an amending document
(transactions/behaviours.refuse_if_journalized), and unjournalizing stays possible:
``POST /wcapi/<model>/<id>/unjournalize/ {"reason": "..."}``. It reverses the record's GL postings
(mirror entries; nothing is erased), clears the journal lock, and stamps who and why in the
record's ``comments.process`` with source ``unjournalize`` — the entry Alice's weekly scrub counts
as a fault signal. Frequent use is the defect to find.
~/Allie/readmes/assessments/2026-09-24-one-route-per-verb.md §16d
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from apps.core.services.door import Refused

logger = logging.getLogger(__name__)

#: every journalizable header (validate_status.JOURNALIZABLE_MODELS, headers only)
UNJOURNALIZE_MODELS = ('invoice', 'cash', 'purchase', 'receipt', 'workorder')


def unjournalize(ctx) -> Dict[str, Any]:
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    from apps.core.services.comment_stamp import append_comment
    from apps.transactions.services.validate_status import is_journalized

    obj = ctx.obj
    reason = str((ctx.data or {}).get('reason') or '').strip()
    if not reason:
        raise Refused(400, 'reason_required',
                      'Say why this must be unjournalized; an amending document is the usual way '
                      '(a return line, an adjustment invoice, a count workorder).', ctx.model_key)
    # Posting locks the record (is_locked); dt_journaled marks it too. Either is journalized.
    if not (getattr(obj, 'is_locked', False) or is_journalized(obj)):
        raise Refused(409, 'not_journalized', f'{ctx.model_key} {obj.pk} is not journalized.', obj.pk)

    reversed_count = reverse_gl_entries(obj, reason=reason)
    user = getattr(ctx.actor, 'user', None)
    append_comment(obj, 'process', f'Unjournalized: {reason}', user=user, source='unjournalize')
    obj.dt_journaled = 0
    obj.is_locked = False
    obj.save(update_fields=['dt_journaled', 'is_locked', 'comments', 'dt_modified', 'version'])
    logger.warning('[unjournalize] %s %s by %s: %s (%d GL rows reversed)', ctx.model_key, obj.pk,
                   getattr(user, 'pk', ctx.actor.kind), reason, reversed_count)
    return {'id': obj.pk, 'reversed': reversed_count, 'reason': reason}


def register() -> None:
    from apps.core.services.verbs import register_command
    for model_key in UNJOURNALIZE_MODELS:
        register_command(model_key, 'unjournalize', unjournalize)
