from __future__ import annotations

"""Processor for PendingInventoryAdjustment rows.

Usage (programmatic):
    from apps.products.services.inventory_adjustment_processor import process_pending_inventory
    summary = process_pending_inventory(limit=50)
    print(summary)

Intended to be idempotent and safe for concurrent execution (uses row locking
with SKIP LOCKED where supported). Can be invoked by a cron / Celery beat or
manually via the management command `process_pending_inventory`.
"""

from typing import Dict, Any
from django.db import transaction, models
from django.utils import timezone

from apps.products.models.inventory_layer import (
    PendingInventoryAdjustment, InventoryLayer,
)
from apps.products.models.processor_runs import InventoryAdjustmentProcessorRun


def process_pending_inventory(limit: int = 100, apply_insufficient: bool = False, cancel_on_insufficient: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Process pending inventory adjustments.

    Parameters:
        limit: Max number of pending rows to attempt this run.
        apply_insufficient: If True, force apply even if remaining < qty (will drive negative remaining). Rare; normally False.
        cancel_on_insufficient: If True, cancel rows that still cannot be applied due to insufficient quantity.
        dry_run: Simulate without persisting changes.

    Returns summary dict with counters.
    """
    applied = skipped_locked = still_locked = insufficient = canceled = attempted = 0
    reserved_conflict_skipped = 0
    started = timezone.now()
    pending_qs = (PendingInventoryAdjustment.objects
                  .select_related('stack')
                  .filter(state=PendingInventoryAdjustment.STATE_PENDING)
                  .order_by('dt_created')[:limit])

    # We'll lock rows inside a loop using select_for_update(skip_locked=True) batches
    ids = list(pending_qs.values_list('id', flat=True))
    if not ids:
        return {"attempted": 0, "applied": 0, "skipped_locked": 0, "still_locked": 0, "insufficient": 0, "canceled": 0, "reserved_conflict_skipped": 0, "dry_run": dry_run}

    for pid in ids:
        attempted += 1
        with transaction.atomic():
            try:
                row_qs = (PendingInventoryAdjustment.objects
                          .select_for_update(skip_locked=True)
                          .select_related('stack')
                          .filter(id=pid, state=PendingInventoryAdjustment.STATE_PENDING))
                padj = row_qs.first()
                if padj is None:  # locked elsewhere or already processed
                    skipped_locked += 1
                    continue
                stack = padj.stack
                if stack.is_locked:
                    still_locked += 1
                    continue
                remaining = stack.remaining_qty()
                # If this pending row originated from reservation conflict, ensure we also subtract active reservations
                if padj.reason == 'reserved_conflict' and not apply_insufficient:
                    from apps.products.models.inventory_reservation import InventoryReservation  # local import to avoid circular
                    active_reserved = (InventoryReservation.objects
                                       .filter(stack=stack,
                                               state=InventoryReservation.STATE_PENDING,
                                               expires_at__gt=timezone.now())
                                       .aggregate(total_qty=models.Sum('qty'))['total_qty'] or 0)
                    # Only safe to apply if remaining - active_reserved >= qty
                    if (remaining - active_reserved) < padj.qty:
                        reserved_conflict_skipped += 1
                        continue
                if remaining < padj.qty and not apply_insufficient:
                    insufficient += 1
                    if cancel_on_insufficient:
                        if not dry_run:
                            padj.cancel("insufficient_qty")
                        else:
                            canceled += 1  # reflect potential future cancellation
                    continue
                # Apply
                if not dry_run:
                    stack.mark_issue(padj.qty)
                    stack.save(update_fields=["quantity", "dt_modified", "version"])
                    padj.state = PendingInventoryAdjustment.STATE_APPLIED
                    padj.dt_applied = timezone.now()
                    padj.save(update_fields=["state", "dt_applied"])
                applied += 1
            except Exception:
                # Best-effort; swallow to keep loop robust. Could add logging.
                continue

    summary = {
        "attempted": attempted,
        "applied": applied,
        "skipped_locked": skipped_locked,
        "still_locked": still_locked,
        "insufficient": insufficient,
        "canceled": canceled,
        "dry_run": dry_run,
        "reserved_conflict_skipped": reserved_conflict_skipped,
        "duration_s": (timezone.now() - started).total_seconds(),
    }
    try:
        InventoryAdjustmentProcessorRun.objects.create(
            run_type=InventoryAdjustmentProcessorRun.RUN_GLOBAL,
            stack_id=None,
            dt_started=started,
            dt_finished=timezone.now(),
            duration_s=summary['duration_s'],
            attempted=attempted,
            applied=applied,
            skipped_locked=skipped_locked,
            still_locked=still_locked,
            insufficient=insufficient,
            canceled=canceled,
            reserved_conflict_skipped=reserved_conflict_skipped,
            dry_run=dry_run,
            summary=summary,
        )
    except Exception:
        pass
    return summary

def process_pending_for_stack(stack_id: int, apply_insufficient: bool = False, cancel_on_insufficient: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Process pending adjustments for a single stack.

    More targeted than global processor; invoked on unlock events.
    """
    applied = insufficient = canceled = attempted = 0
    reserved_conflict_skipped = 0
    started = timezone.now()
    # Filter pending rows for this stack ordered FIFO
    ids = list(PendingInventoryAdjustment.objects.filter(
        stack_id=stack_id,
        state=PendingInventoryAdjustment.STATE_PENDING
    ).order_by('dt_created').values_list('id', flat=True))
    for pid in ids:
        attempted += 1
        with transaction.atomic():
            row_qs = (PendingInventoryAdjustment.objects
                      .select_for_update(skip_locked=True)
                      .select_related('stack')
                      .filter(id=pid, state=PendingInventoryAdjustment.STATE_PENDING))
            padj = row_qs.first()
            if not padj:
                continue
            stack = padj.stack
            if stack.is_locked:
                # Still locked; abort loop early (future attempts will retry)
                break
            remaining = stack.remaining_qty()
            if padj.reason == 'reserved_conflict' and not apply_insufficient:
                from apps.products.models.inventory_reservation import InventoryReservation
                active_reserved = (InventoryReservation.objects
                                   .filter(stack=stack,
                                           state=InventoryReservation.STATE_PENDING,
                                           expires_at__gt=timezone.now())
                                   .aggregate(total_qty=models.Sum('qty'))['total_qty'] or 0)
                if (remaining - active_reserved) < padj.qty:
                    reserved_conflict_skipped += 1
                    continue
            if remaining < padj.qty and not apply_insufficient:
                insufficient += 1
                if cancel_on_insufficient and not dry_run:
                    padj.cancel("insufficient_qty")
                    canceled += 1
                continue
            # Apply now
            if not dry_run:
                stack.mark_issue(padj.qty)
                stack.save(update_fields=["quantity", "dt_modified", "version"])
                padj.state = PendingInventoryAdjustment.STATE_APPLIED
                padj.dt_applied = timezone.now()
                padj.save(update_fields=["state", "dt_applied"])
            applied += 1
    summary = {
        "stack_id": stack_id,
        "attempted": attempted,
        "applied": applied,
        "insufficient": insufficient,
        "canceled": canceled,
        "dry_run": dry_run,
        "reserved_conflict_skipped": reserved_conflict_skipped,
        "duration_s": (timezone.now() - started).total_seconds(),
    }
    try:
        InventoryAdjustmentProcessorRun.objects.create(
            run_type=InventoryAdjustmentProcessorRun.RUN_STACK,
            stack_id=stack_id,
            dt_started=started,
            dt_finished=timezone.now(),
            duration_s=summary['duration_s'],
            attempted=attempted,
            applied=applied,
            skipped_locked=0,
            still_locked=0,
            insufficient=insufficient,
            canceled=canceled,
            reserved_conflict_skipped=reserved_conflict_skipped,
            dry_run=dry_run,
            summary=summary,
        )
    except Exception:
        pass
    return summary

__all__ = ["process_pending_inventory", "process_pending_for_stack"]
