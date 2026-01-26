"""
Pending Inventory Processor for Line Item Changes.

Processes Pending records created by LineItemService to update Item
inventory quantities (on_so, on_po, on_wo, invoiced, etc.).

This decouples transaction line changes from Item record updates,
reducing lock contention and improving throughput.

Similar to WebClerk2's TallyInventoryProcess but modernized for Django.

Usage:
    from apps.transactions.services.pending_inventory_processor import (
        process_line_item_pending,
        process_pending_for_item,
    )
    
    # Process all pending
    summary = process_line_item_pending(limit=100)
    
    # Process for specific item
    summary = process_pending_for_item(item_id=123)
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional, TypedDict

from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Pending
from apps.products.models import Item

# Import trace debugging utilities
from apps.transactions.services.trace_debug import (
    trace_pending_processing_start,
    trace_pending_processing_complete,
    should_trace,
)

logger = logging.getLogger(__name__)


# Purposes handled by this processor (from LineItemService)
HANDLED_PURPOSES = (
    'inventory_line_add',
    'inventory_qty_change',
    'inventory_line_delete',
    'inventory_cost_change',
)


class ProcessingSummary(TypedDict, total=False):
    """Summary of processing results."""
    total_found: int
    processed: int
    skipped_locked: int
    skipped_missing_item: int
    errors: int
    dry_run: bool


def process_line_item_pending(
    limit: int = 100,
    dry_run: bool = False,
    item_id: Optional[int] = None,
    force_locked: bool = False,
) -> ProcessingSummary:
    """
    Process pending line item inventory changes.
    
    Queries unprocessed Pending records and applies the quantity
    changes to Item records.
    
    Args:
        limit: Maximum records to process per run
        dry_run: If True, simulate without saving
        item_id: If provided, only process records for this item
        force_locked: If True, attempt to process even if item is locked
        
    Returns:
        Summary dict with processing statistics
    """
    summary: ProcessingSummary = {
        'total_found': 0,
        'processed': 0,
        'skipped_locked': 0,
        'skipped_missing_item': 0,
        'errors': 0,
        'dry_run': dry_run,
    }
    
    # Build query for unprocessed pending records
    query = Q(
        model_name='item',
        purpose__in=HANDLED_PURPOSES,
        dt_processed=0,  # Not yet processed
    )
    
    if item_id:
        query &= Q(record_id=str(item_id))
    
    # Get pending records ordered by creation (FIFO)
    pending_records = Pending.objects.filter(query).order_by('dt_created')[:limit]
    summary['total_found'] = pending_records.count()
    
    if summary['total_found'] == 0:
        logger.debug("No pending line item records to process.")
        return summary
    
    logger.info(f"Processing {summary['total_found']} pending line item records (dry_run={dry_run})")
    
    # Group by item_id for efficient processing
    item_pending_map: Dict[int, list] = {}
    for pending in pending_records:
        pending_item_id = pending.data.get('item_id')
        if pending_item_id:
            if pending_item_id not in item_pending_map:
                item_pending_map[pending_item_id] = []
            item_pending_map[pending_item_id].append(pending)
    
    # Process each item's pending records
    for item_pk, pending_list in item_pending_map.items():
        try:
            result = _process_pending_for_item(
                item_pk=item_pk,
                pending_records=pending_list,
                dry_run=dry_run,
                force_locked=force_locked,
            )
            summary['processed'] += result.get('processed', 0)
            summary['skipped_locked'] += result.get('skipped_locked', 0)
            summary['skipped_missing_item'] += result.get('skipped_missing_item', 0)
        except Exception as e:
            logger.error(f"Error processing pending for item {item_pk}: {e}")
            summary['errors'] += len(pending_list)
    
    logger.info(
        f"Completed: processed={summary['processed']}, "
        f"skipped_locked={summary['skipped_locked']}, "
        f"skipped_missing={summary['skipped_missing_item']}, "
        f"errors={summary['errors']}"
    )
    
    return summary


def process_pending_for_item(
    item_id: int,
    dry_run: bool = False,
    force_locked: bool = False,
) -> ProcessingSummary:
    """
    Process all pending records for a specific item.
    
    Args:
        item_id: The item ID to process
        dry_run: If True, simulate without saving
        force_locked: If True, attempt even if locked
        
    Returns:
        Summary dict
    """
    return process_line_item_pending(
        limit=1000,  # Higher limit for single-item processing
        dry_run=dry_run,
        item_id=item_id,
        force_locked=force_locked,
    )


def _process_pending_for_item(
    item_pk: int,
    pending_records: list,
    dry_run: bool = False,
    force_locked: bool = False,
) -> Dict[str, int]:
    """
    Internal: Process pending records for a single item.
    
    Aggregates all quantity deltas and applies them in a single update.
    """
    result = {
        'processed': 0,
        'skipped_locked': 0,
        'skipped_missing_item': 0,
    }
    
    # Get the item
    try:
        item = Item.objects.select_for_update(nowait=True).get(pk=item_pk)
    except Item.DoesNotExist:
        logger.warning(f"Item {item_pk} not found, marking pending records as skipped")
        result['skipped_missing_item'] = len(pending_records)
        return result
    except Exception as e:
        # Could be locked
        if not force_locked:
            logger.debug(f"Item {item_pk} appears locked, skipping: {e}")
            result['skipped_locked'] = len(pending_records)
            return result
        # Force mode - try regular get
        item = Item.objects.get(pk=item_pk)
    
    # TRACE: Processing start
    trace_pending_processing_start(
        item_id=item_pk,
        item_ida=item.ida or item.sku or item.name,
        pending_count=len(pending_records),
        current_quantity=item.quantity or {},
    )
    
    # Aggregate quantity changes from all pending records
    on_so_delta = Decimal('0')
    on_po_delta = Decimal('0')
    on_wo_delta = Decimal('0')
    on_p_delta = Decimal('0')
    invoiced_delta = Decimal('0')
    
    for pending in pending_records:
        data = pending.data or {}
        on_so_delta += Decimal(str(data.get('on_so', 0) or 0))
        on_po_delta += Decimal(str(data.get('on_po', 0) or 0))
        on_wo_delta += Decimal(str(data.get('on_wo', 0) or 0))
        on_p_delta += Decimal(str(data.get('on_p', 0) or 0))
        invoiced_delta += Decimal(str(data.get('invoiced', 0) or 0))
    
    logger.debug(
        f"Item {item_pk}: SO={on_so_delta:+}, PO={on_po_delta:+}, "
        f"WO={on_wo_delta:+}, PP={on_p_delta:+}, IV={invoiced_delta:+}"
    )
    
    if dry_run:
        logger.info(f"[DRY RUN] Would update item {item_pk} quantities")
        result['processed'] = len(pending_records)
        return result
    
    # Apply updates within a transaction
    with db_transaction.atomic():
        # Get current values from item.quantity JSON
        quantity = item.quantity or {}
        
        # Update quantity buckets
        current_so = Decimal(str(quantity.get('on_so', 0) or 0))
        current_po = Decimal(str(quantity.get('on_po', 0) or 0))
        current_wo = Decimal(str(quantity.get('on_wo', 0) or 0))
        current_p = Decimal(str(quantity.get('on_p', 0) or 0))
        current_invoiced = Decimal(str(quantity.get('invoiced', 0) or 0))
        current_on_hand = Decimal(str(quantity.get('on_hand', 0) or 0))
        
        quantity['on_so'] = float(current_so + on_so_delta)
        quantity['on_po'] = float(current_po + on_po_delta)
        quantity['on_wo'] = float(current_wo + on_wo_delta)
        quantity['on_p'] = float(current_p + on_p_delta)
        quantity['invoiced'] = float(current_invoiced + invoiced_delta)
        
        # Invoicing reduces on_hand (negative invoiced delta = return adds back)
        if invoiced_delta != 0:
            quantity['on_hand'] = float(current_on_hand - invoiced_delta)
            # Recompute available
            alloc = Decimal(str(quantity.get('allocated', 0) or 0))
            quantity['available'] = float(Decimal(str(quantity['on_hand'])) - alloc)
        
        # Update the item using .update() to avoid full save() with all its hooks
        Item.objects.filter(pk=item_pk).update(quantity=quantity)
        
        # Mark all pending records as processed
        now_ts = int(timezone.now().timestamp() * 1000)
        for pending in pending_records:
            pending.dt_processed = now_ts
            pending.save(update_fields=['dt_processed', 'dt_modified', 'version'])
    
    # Refresh item from DB to get updated quantity for trace
    item.refresh_from_db()
    
    # TRACE: Processing complete
    deltas = {}
    if on_so_delta: deltas['on_so'] = f'{on_so_delta:+}'
    if on_po_delta: deltas['on_po'] = f'{on_po_delta:+}'
    if on_wo_delta: deltas['on_wo'] = f'{on_wo_delta:+}'
    if on_p_delta: deltas['on_p'] = f'{on_p_delta:+}'
    if invoiced_delta: deltas['invoiced'] = f'{invoiced_delta:+}'
    trace_pending_processing_complete(
        item_id=item_pk,
        item_ida=item.ida or item.sku or item.name,
        deltas=deltas,
        new_quantity=item.quantity or {},
    )
    
    result['processed'] = len(pending_records)
    
    logger.info(
        f"Applied {len(pending_records)} pending changes to item {item_pk} "
        f"({item.ida or item.name})"
    )
    
    return result
