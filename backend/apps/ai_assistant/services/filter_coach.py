"""Alice watches rejected API filters.

A filter naming a field the model does not have is a question the caller asked
badly. WC3 answers with coaching (wcapi.UnknownFilterError) and Alice keeps the
record so the same wrong question gets fixed instead of repeated.

Escalation ladder (Bill, 2026-09-17):
  1. Alice records it and recommends the fix (this module).
  2. Repeats she cannot resolve go to WC_HQ, where Allie, Alice-HQ and Claude work it.
  3. Still unresolved: ask Bill.
"""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

IMPORTANT_AFTER = 3     # the same wrong filter three times is a pattern, not a slip
ESCALATE_AFTER = 10     # Alice has not resolved it; WC_HQ takes it


def observe_unknown_filter(model_key: str, fields: List[str], hints: List[str],
                           caller: str = '', contact_id: Optional[int] = None) -> None:
    """Record one rejected filter. Never raises — coaching must not break a request."""
    try:
        from django.db import transaction
        from apps.ai_assistant.models.alice import AliceObservation

        dedup_key = f"unknown_filter:{model_key}:{','.join(sorted(fields))}"[:200]
        message = f"Filter rejected on {model_key}: {', '.join(fields)}"
        with transaction.atomic():
            prior = (AliceObservation.objects
                     .filter(dedup_key=dedup_key, acknowledged=False)
                     .order_by('-id').first())
            seen = (prior.times_used + 1) if prior else 1
            if seen >= ESCALATE_AFTER:
                category, priority = 'escalation', 2
                next_step = ('Unresolved after %d rejections — WC_HQ (Allie, Alice-HQ, Claude). '
                             'If they cannot resolve it, ask Bill.' % seen)
            elif seen >= IMPORTANT_AFTER:
                category, priority = 'coaching', 1
                next_step = 'Repeating — Alice recommends the fix to the caller.'
            else:
                category, priority = 'coaching', 0
                next_step = 'Alice recommends the fix to the caller.'

            detail = '\n'.join(
                [f"seen: {seen}", f"caller: {caller or 'unknown'}", f"next: {next_step}", ''] + hints)
            if prior:
                prior.times_used = seen
                prior.category, prior.priority = category, priority
                prior.detail = detail[:2000]
                prior.save(update_fields=['times_used', 'category', 'priority', 'detail',
                                          'dt_modified', 'version'])
            else:
                AliceObservation.objects.create(
                    category=category, source='alice', priority=priority,
                    message=message[:500], detail=detail[:2000],
                    model_name=model_key[:50], times_used=1,
                    contact_id=contact_id, dedup_key=dedup_key,
                )
    except Exception:  # an observation must never break the request it describes
        logger.exception('[FILTER COACH] could not write observation')
