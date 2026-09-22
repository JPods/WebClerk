"""Inventory availability service.

Provides item availability queries across warehouses/sites.
Available = on_hand - reserved. Does not block overselling — visibility aid only.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)


def available_from_quantity(quantity: Optional[Dict[str, Any]]) -> Optional[float]:
    """The item-level availability formula: available = on_hand - allocated.

    This is the number stored in Item.quantity['available'] and the one every
    caller must use. It is deliberately NOT the layer/reservation calculation in
    get_item_availability() below, which answers a different question from
    InventoryLayer and InventoryReservation rows.

    Anything that needs to derive availability — the item save path, the flight
    simulator's reconstructed history, reports — calls this rather than writing
    `on_hand - allocated` again. A second copy of a formula is a second formula:
    the flight simulator had drifted to a bare `available = on_hand`, so it
    displayed availability that ignored allocation entirely and taught a rule
    the system does not follow.

    Returns None when either ingredient is absent, so callers can leave the
    field alone rather than publishing a number that was never computed.
    """
    if not isinstance(quantity, dict):
        return None
    on_hand = quantity.get('on_hand')
    allocated = quantity.get('allocated')
    if on_hand is None or allocated is None:
        return None
    try:
        return float(on_hand) - float(allocated)
    except (TypeError, ValueError):
        return None


def get_item_availability(
    item_id: int,
    warehouse_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get inventory availability for an item, optionally filtered by warehouse.

    Returns aggregate quantities across all matching InventoryLayers.
    Available = on_hand - reserved (visibility aid, not a hard block).
    """
    from apps.products.models import InventoryLayer
    from apps.products.models.inventory_reservation import InventoryReservation

    filters = Q(item_id=item_id, is_active=True)
    if warehouse_id:
        filters &= Q(warehouse_id=warehouse_id)

    layers = InventoryLayer.objects.filter(filters)

    on_hand = Decimal('0')
    on_so = Decimal('0')
    on_po = Decimal('0')

    for layer in layers:
        qty = layer.quantity if isinstance(layer.quantity, dict) else {}
        on_hand += Decimal(str(qty.get('on_hand', 0) or 0))
        on_so += Decimal(str(qty.get('on_so', 0) or 0))
        on_po += Decimal(str(qty.get('on_po', 0) or 0))

    # Active reservations reduce available
    reserved = Decimal('0')
    res_filters = Q(item_id=item_id, is_active=True)
    if warehouse_id:
        res_filters &= Q(warehouse_id=warehouse_id)
    try:
        from django.db.models import Sum
        res_sum = InventoryReservation.objects.filter(
            res_filters
        ).aggregate(total=Sum('quantity'))
        reserved = Decimal(str(res_sum['total'] or 0))
    except Exception:
        pass

    available = on_hand - reserved

    return {
        'item_id': item_id,
        'warehouse_id': warehouse_id,
        'on_hand': float(on_hand),
        'on_so': float(on_so),
        'on_po': float(on_po),
        'reserved': float(reserved),
        'available': float(available),
    }


def get_item_availability_by_warehouse(item_id: int) -> List[Dict[str, Any]]:
    """Get availability breakdown per warehouse for an item."""
    from apps.products.models import InventoryLayer

    warehouse_ids = (
        InventoryLayer.objects
        .filter(item_id=item_id, is_active=True)
        .values_list('warehouse_id', flat=True)
        .distinct()
    )

    results = []
    for wh_id in warehouse_ids:
        avail = get_item_availability(item_id, warehouse_id=wh_id)
        results.append(avail)

    return results
