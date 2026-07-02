"""
Inventory Pending Service — ONE PATH for all item.quantity changes.

Every inventory change creates a PendingInventoryAdjustment record first.
If item is unlocked → apply immediately.
If item is locked → queue as pending, apply when unlocked.

One path, one audit trail. No direct writes to item.quantity.

Called from: order_production.py, inventory_stacks.py, and any future service
that modifies item quantities.
"""
from __future__ import annotations
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.products.models.item import Item
from apps.products.models.inventory_layer import PendingInventoryAdjustment, InventoryLayer
import time


def _now_ms():
    return int(time.time() * 1000)


def adjust_item_quantity(
    item_id: int,
    field: str,
    delta: int | float,
    reason: str = '',
    source_type: str = '',
    source_id: int = None,
    source_line_id: int = None,
    inventory_layer_id: int = None,
) -> dict:
    """Create a pending adjustment and apply if item is unlocked.

    This is the ONLY function that modifies item.quantity. All inventory
    services must call this instead of writing item.quantity directly.

    Args:
        item_id: Item PK
        field: quantity field to change ('on_hand', 'on_po', 'on_so', 'on_p', etc.)
        delta: amount to add (positive) or subtract (negative)
        reason: human-readable reason ('invoice_ship', 'po_receive', 'proposal_add', etc.)
        source_type: model name of the source transaction
        source_id: PK of the source transaction
        source_line_id: PK of the source line item
        inventory_layer_id: FK to InventoryLayer (if applicable, e.g., for receiving/consuming)

    Returns:
        {pending_id, state, field, delta, applied}
    """
    item = Item.objects.get(pk=item_id)

    # Find or create a dummy layer if none provided (for non-layer adjustments like on_p, on_so)
    if inventory_layer_id:
        layer = InventoryLayer.objects.get(pk=inventory_layer_id)
    else:
        # Use or create a placeholder layer for this item
        layer, _ = InventoryLayer.objects.get_or_create(
            item_id=item_id,
            source_doc_type='system',
            source_doc_id=0,
            defaults={
                'quantity': {'received': 0, 'issued': 0, 'scrapped': 0},
                'cost': {},
                'lot': '',
                'serial_numbers': [],
                'is_locked': False,
                'warehouse_id': 1,  # default warehouse
                'dt_created': _now_ms(),
                'dt_modified': _now_ms(),
            }
        )

    # Create pending record — always
    pending = PendingInventoryAdjustment.objects.create(
        inventory_layer=layer,
        qty=Decimal(str(delta)),
        state=PendingInventoryAdjustment.STATE_PENDING,
        reason=reason[:80],
        request_ref={
            'item_id': item_id,
            'field': field,
            'delta': float(delta),
            'source_type': source_type,
            'source_id': source_id,
            'source_line_id': source_line_id,
            'dt_requested': _now_ms(),
        },
    )

    # Try to apply immediately if item is not locked
    applied = False
    item.refresh_from_db()

    if not item.is_locked:
        with transaction.atomic():
            item = Item.objects.select_for_update().get(pk=item_id)
            q = item.quantity or {}
            current = q.get(field, 0)
            q[field] = current + float(delta)
            # Recalculate available
            q['available'] = q.get('on_hand', 0)
            item.quantity = q
            item.row_version = (item.row_version or 0) + 1
            item.dt_modified = _now_ms()
            item.save(update_fields=['quantity', 'row_version', 'dt_modified'])

            pending.state = PendingInventoryAdjustment.STATE_APPLIED
            pending.dt_applied = timezone.now()
            pending.save()
            applied = True

    return {
        'pending_id': pending.pk,
        'state': pending.state,
        'field': field,
        'delta': float(delta),
        'applied': applied,
        'item_id': item_id,
    }


def apply_pending_for_item(item_id: int) -> dict:
    """Apply all pending adjustments for an item. Call after unlocking.

    Returns: {applied_count, still_pending}
    """
    item = Item.objects.get(pk=item_id)
    if item.is_locked:
        return {'applied_count': 0, 'still_pending': 0, 'error': 'item is locked'}

    pendings = PendingInventoryAdjustment.objects.filter(
        request_ref__item_id=item_id,
        state=PendingInventoryAdjustment.STATE_PENDING,
    ).order_by('id')

    applied_count = 0

    with transaction.atomic():
        item = Item.objects.select_for_update().get(pk=item_id)
        q = item.quantity or {}

        for p in pendings:
            ref = p.request_ref or {}
            field = ref.get('field', 'on_hand')
            delta = ref.get('delta', float(p.qty))
            current = q.get(field, 0)
            q[field] = current + delta

            p.state = PendingInventoryAdjustment.STATE_APPLIED
            p.dt_applied = timezone.now()
            p.save()
            applied_count += 1

        q['available'] = q.get('on_hand', 0)
        item.quantity = q
        item.row_version = (item.row_version or 0) + 1
        item.dt_modified = _now_ms()
        item.save(update_fields=['quantity', 'row_version', 'dt_modified'])

    still_pending = PendingInventoryAdjustment.objects.filter(
        request_ref__item_id=item_id,
        state=PendingInventoryAdjustment.STATE_PENDING,
    ).count()

    return {'applied_count': applied_count, 'still_pending': still_pending}


def get_pending_for_item(item_id: int) -> list:
    """Get all pending adjustments for an item.

    Returns: [{pending_id, field, delta, reason, state, dt_requested}]
    """
    pendings = PendingInventoryAdjustment.objects.filter(
        request_ref__item_id=item_id,
    ).order_by('-id')

    return [{
        'pending_id': p.pk,
        'field': (p.request_ref or {}).get('field', '?'),
        'delta': float(p.qty),
        'reason': p.reason,
        'state': p.state,
        'source_type': (p.request_ref or {}).get('source_type', ''),
        'source_id': (p.request_ref or {}).get('source_id'),
        'dt_requested': (p.request_ref or {}).get('dt_requested'),
        'dt_applied': p.dt_applied.isoformat() if p.dt_applied else None,
    } for p in pendings]
