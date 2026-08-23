"""Inventory reservation services — soft holds with TTL and order allocation.

Replaces WC2's non-journalable invoice hack with a dedicated reservation model.
Reservations hold inventory without touching the Invoice table or GL.

Lifecycle: pending → committed (real issue) | canceled | expired (auto-reclaimed)
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def create_reservation(
    layer: InventoryLayer,
    qty,
    *,
    ttl_seconds: int = 86400,
    reason: str = '',
    context: dict | None = None,
) -> InventoryReservation:
    """Create a reservation if sufficient remaining (excluding other active reservations).

    Default TTL is 24 hours. For carts use 900 (15 min). For confirmed orders use 86400+.
    """
    qty_dec = Decimal(str(qty))
    if qty_dec <= 0:
        raise ValueError('qty must be > 0')

    available = availability_for_layer(layer)
    if available < qty_dec:
        raise ValueError(
            f'Insufficient available for reservation: need {qty_dec}, available {available} '
            f'(remaining {layer.remaining_qty()} minus active reservations)'
        )

    return InventoryReservation.objects.create(
        item=layer.item,
        item_ida=layer.item_ida,
        description=f'Hold {qty_dec} × {layer.item_ida} ({reason})',
        warehouse=layer.warehouse,
        inventory_layer=layer,
        qty=qty_dec,
        dt_expires=timezone.now() + timedelta(seconds=ttl_seconds),
        reason=reason[:80],
        context=context or {},
    )


def commit_reservation(reservation_id: int) -> bool:
    """Convert a pending reservation to a real inventory issue.

    Called when an order ships / invoice is confirmed.
    """
    res = InventoryReservation.objects.get(id=reservation_id)
    return res.commit()


def release_reservation(reservation_id: int, reason: str = 'canceled') -> bool:
    """Release a pending reservation — puts inventory back.

    Called when an order is canceled or modified.
    """
    res = InventoryReservation.objects.get(id=reservation_id)
    return res.release(reason)


# ---------------------------------------------------------------------------
# Order allocation workflow
# ---------------------------------------------------------------------------

@transaction.atomic
def reserve_for_order(
    item_id: int,
    qty,
    *,
    order_id: int | None = None,
    order_line_id: int | None = None,
    warehouse_id: int | None = None,
    ttl_seconds: int = 86400 * 7,
) -> list[InventoryReservation]:
    """Allocate inventory for an order across available layers (FIFO).

    Splits across multiple layers if no single layer has enough.
    Returns list of reservations created.
    """
    qty_remaining = Decimal(str(qty))
    reservations = []

    qs = InventoryLayer.objects.filter(item_id=item_id).order_by('id')  # FIFO
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    for layer in qs:
        if qty_remaining <= 0:
            break
        available = availability_for_layer(layer)
        if available <= 0:
            continue

        take = min(available, qty_remaining)
        res = create_reservation(
            layer, take,
            ttl_seconds=ttl_seconds,
            reason='order_allocation',
            context={
                'order_id': order_id,
                'order_line_id': order_line_id,
            },
        )
        reservations.append(res)
        qty_remaining -= take

    if qty_remaining > 0:
        # Partial allocation — record what couldn't be reserved
        # The caller decides whether to backorder or reject
        pass

    return reservations


@transaction.atomic
def commit_order_reservations(order_id: int) -> int:
    """Commit all pending reservations for an order (when invoice ships)."""
    reservations = InventoryReservation.objects.filter(
        state=InventoryReservation.STATE_PENDING,
        context__order_id=order_id,
    )
    committed = 0
    for res in reservations:
        if res.commit():
            committed += 1
    return committed


@transaction.atomic
def release_order_reservations(order_id: int, reason: str = 'order_canceled') -> int:
    """Release all pending reservations for a canceled order."""
    reservations = InventoryReservation.objects.filter(
        state=InventoryReservation.STATE_PENDING,
        context__order_id=order_id,
    )
    released = 0
    for res in reservations:
        if res.release(reason):
            released += 1
    return released


# ---------------------------------------------------------------------------
# Availability and maintenance
# ---------------------------------------------------------------------------

def availability_for_layer(layer: InventoryLayer) -> Decimal:
    """Remaining qty minus active reservations for a specific layer."""
    now = timezone.now()
    active_reserved = (
        InventoryReservation.objects
        .filter(inventory_layer=layer, state=InventoryReservation.STATE_PENDING, dt_expires__gt=now)
        .aggregate(total=Sum('qty'))['total'] or Decimal('0')
    )
    return Decimal(str(layer.remaining_qty())) - Decimal(str(active_reserved))


def availability_for_item(item_id: int, warehouse_id: int | None = None) -> Decimal:
    """Total available qty for an item across all layers (minus reservations)."""
    qs = InventoryLayer.objects.filter(item_id=item_id)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    total = Decimal('0')
    for layer in qs:
        avail = availability_for_layer(layer)
        if avail > 0:
            total += avail
    return total


def release_expired(batch: int = 500) -> dict:
    """Reclaim expired reservations. Run as a nightly Celery task."""
    now = timezone.now()
    qs = InventoryReservation.objects.filter(
        state=InventoryReservation.STATE_PENDING,
        dt_expires__lte=now,
    )[:batch]
    count = 0
    for r in qs:
        r.mark_expired()
        count += 1
    return {'expired': count}


def active_reservations_for_item(item_id: int) -> list[dict]:
    """Summary of active reservations for an item — useful for JSON viewer display."""
    now = timezone.now()
    reservations = InventoryReservation.objects.filter(
        item_id=item_id,
        state=InventoryReservation.STATE_PENDING,
        dt_expires__gt=now,
    ).select_related('warehouse', 'inventory_layer').order_by('dt_expires')

    return [{
        'id': r.id,
        'qty': float(r.qty),
        'warehouse': r.warehouse.code if r.warehouse else '',
        'layer_id': r.inventory_layer_id,
        'expires': r.dt_expires.isoformat(),
        'reason': r.reason,
        'context': r.context,
    } for r in reservations]


__all__ = [
    'create_reservation', 'commit_reservation', 'release_reservation',
    'reserve_for_order', 'commit_order_reservations', 'release_order_reservations',
    'availability_for_layer', 'availability_for_item',
    'release_expired', 'active_reservations_for_item',
]
