"""
Pending Inventory Processor — the queue drain.

A Pending record tries to apply itself when it is saved (Pending.try_apply).
When the item is locked it stays unprocessed, and this module picks it up later
(celery, the management command, or a layer being unlocked).

It applies each record through the same Pending.try_apply a live save uses.
Everything an apply does — the item's buckets, the line's event, and the layer
that must move with on_hand — happens in one place, whichever path gets there
first (Bill, 2026-09-21: "Layers must change with items").

This used to sum every record's buckets and write the item in one .update().
That was a second applier: it never recorded line events, it would have skipped
the layer, and its own purpose list had drifted from Pending's, so an
'allocation' or 'line_event' that met a lock was never retried.

Usage:
    from apps.transactions.services.inventory_pending_process import (
        process_line_item_pending,
        process_pending_for_item,
    )

    summary = process_line_item_pending(limit=100)     # everything waiting
    summary = process_pending_for_item(item_id=123)    # one item
"""

import logging
from typing import Optional, TypedDict

from django.db.models import Q

from apps.core.models import Pending
from apps.core.models.pending import INVENTORY_PURPOSES

logger = logging.getLogger(__name__)


class ProcessingSummary(TypedDict, total=False):
    """Summary of processing results."""
    total_found: int
    processed: int
    skipped_locked: int
    errors: int
    dry_run: bool


def process_line_item_pending(
    limit: int = 100,
    dry_run: bool = False,
    item_id: Optional[int] = None,
) -> ProcessingSummary:
    """Apply unprocessed inventory Pending records, oldest first.

    A record that is still locked stays unprocessed for the next drain. A record
    that raises is counted as an error and also stays unprocessed: its apply rolled
    back whole, so the item and its layer still agree.
    """
    summary: ProcessingSummary = {
        'total_found': 0,
        'processed': 0,
        'skipped_locked': 0,
        'errors': 0,
        'dry_run': dry_run,
    }

    query = Q(model_name='item', purpose__in=INVENTORY_PURPOSES, dt_processed=0)
    if item_id:
        query &= Q(record_id=str(item_id))

    pending_records = list(Pending.objects.filter(query).order_by('dt_created')[:limit])
    summary['total_found'] = len(pending_records)
    if not pending_records:
        logger.debug("No pending inventory records to process.")
        return summary

    logger.info(f"Processing {summary['total_found']} pending inventory records (dry_run={dry_run})")

    for pending in pending_records:
        if dry_run:
            summary['processed'] += 1
            continue
        try:
            if pending.try_apply():
                summary['processed'] += 1
            else:
                summary['skipped_locked'] += 1
        except Exception as e:
            logger.error(f"Pending {pending.pk} (item {pending.record_id}) failed to apply: {e}")
            summary['errors'] += 1

    logger.info(
        f"Completed: processed={summary['processed']}, "
        f"skipped_locked={summary['skipped_locked']}, "
        f"errors={summary['errors']}"
    )
    return summary


def process_pending_for_item(item_id: int, dry_run: bool = False) -> ProcessingSummary:
    """Apply every unprocessed inventory Pending record for one item."""
    return process_line_item_pending(limit=1000, dry_run=dry_run, item_id=item_id)
