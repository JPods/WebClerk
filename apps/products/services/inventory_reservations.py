from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation


def create_reservation(stack: InventoryLayer, qty, ttl_seconds: int = 900, reason: str = '', context: dict | None = None) -> InventoryReservation:
    """Create a reservation if sufficient remaining (excluding other active reservations)."""
    qty_dec = Decimal(str(qty))
    if qty_dec <= 0:
        raise ValueError('qty must be > 0')
    # Compute currently reserved qty for stack
    now = timezone.now()
    active_reserved = (InventoryReservation.objects
                       .filter(stack=stack, state=InventoryReservation.STATE_PENDING, expires_at__gt=now)
                       .aggregate(total=__import__('django').db.models.Sum('qty'))['total'] or Decimal('0'))
    remaining = Decimal(str(stack.remaining_qty()))
    active_reserved = Decimal(str(active_reserved))
    available = remaining - active_reserved
    if available < qty_dec:
        raise ValueError('insufficient_available_for_reservation')
    expires_at = now + timedelta(seconds=ttl_seconds)
    return InventoryReservation.objects.create(
        item=stack.item,
        warehouse=stack.warehouse,
        stack=stack,
        qty=qty_dec,
        expires_at=expires_at,
        reason=reason[:80],
        context=context or {},
    )


def release_expired(batch: int = 500):
    now = timezone.now()
    qs = InventoryReservation.objects.filter(state=InventoryReservation.STATE_PENDING, expires_at__lte=now)[:batch]
    count = 0
    for r in qs:
        r.mark_expired()
        count += 1
    return {'expired': count}


def availability_for_stack(stack: InventoryLayer):
    now = timezone.now()
    active_reserved = (InventoryReservation.objects
                       .filter(stack=stack, state=InventoryReservation.STATE_PENDING, expires_at__gt=now)
                       .aggregate(total=__import__('django').db.models.Sum('qty'))['total'] or 0)
    return Decimal(str(stack.remaining_qty())) - Decimal(str(active_reserved))


__all__ = [
    'create_reservation', 'release_expired', 'availability_for_stack'
]
