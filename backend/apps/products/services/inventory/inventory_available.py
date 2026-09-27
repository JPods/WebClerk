"""Inventory availability service.

Item availability from the item's own leaves: available = on_hand − allocated.
Does not block overselling — visibility aid only.
"""
import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def available_from_quantity(quantity: Optional[Dict[str, Any]]) -> Optional[float]:
    """The item-level availability formula: available = on_hand - allocated.

    This is the number stored in Item.quantity['available'] and the one every
    caller must use; get_item_availability() below reports it with the other leaves.

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


def get_item_availability(item_id: int) -> Dict[str, Any]:
    """One item's stock, as its leaves say.

    Bill, 2026-09-26: "Needs to read the leaf, item.quantity.on_hand." Item.quantity is the book
    the applier keeps: on_hand, on_so, on_po, allocated, and available = on_hand − allocated
    (available_from_quantity). There is no reservation (Bill, 2026-09-24), and per-warehouse
    figures wait for the warehouse review (action 31277). Until 2026-09-26 this summed a layer
    'on_hand' key that layers never have, so it always answered 0.
    """
    from apps.products.models import Item

    item = Item.objects.filter(pk=item_id).only('id', 'quantity').first()
    quantity = item.quantity if item is not None and isinstance(item.quantity, dict) else {}

    def leaf(key):
        return float(quantity.get(key) or 0)

    available = available_from_quantity(quantity)
    return {
        'item_id': item_id,
        'on_hand': leaf('on_hand'),
        'on_so': leaf('on_so'),
        'on_po': leaf('on_po'),
        'allocated': leaf('allocated'),
        'available': float(leaf('on_hand') - leaf('allocated') if available is None else available),
    }
