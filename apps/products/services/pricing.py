"""Price resolution service.

Resolves the correct unit price for an item based on price level and quantity.

Resolution chain:
  1. line.price_level (user override — requires authority)
  2. header.price_level (inherited from customer at order creation)
  3. customer.price_level (org default)
  4. 'base' (system fallback)

Within the resolved level, quantity breaks apply if defined.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default price level when no level is set anywhere in the chain
DEFAULT_PRICE_LEVEL = 'base'

# Valid price levels (keys in Item.price JSON)
VALID_PRICE_LEVELS = ('base', 'msrp', 'retail', 'wholesale', 'distributor', 'sample')


def resolve_price_level(
    customer_level: Optional[str] = None,
    header_level: Optional[str] = None,
    line_level: Optional[str] = None,
) -> str:
    """Determine the effective price level from the chain.

    Priority: line > header > customer > default.
    Returns a valid price level key.
    """
    for level in (line_level, header_level, customer_level):
        if level and level.strip():
            cleaned = level.strip().lower()
            if cleaned in VALID_PRICE_LEVELS:
                return cleaned
    return DEFAULT_PRICE_LEVEL


def resolve_unit_price(
    item_price: Dict[str, Any],
    price_level: str,
    quantity: float = 1.0,
) -> Decimal:
    """Resolve the unit price for an item at a given level and quantity.

    Args:
        item_price: The Item.price JSON dict (has keys: base, retail, wholesale, etc.)
        price_level: Resolved price level key (from resolve_price_level)
        quantity: Order quantity — used for quantity break lookup

    Returns:
        Decimal unit price. Falls back through: level → base → 0.
    """
    if not isinstance(item_price, dict):
        return Decimal('0')

    # Try the requested level
    level_price = item_price.get(price_level)
    if level_price is not None and level_price != '':
        try:
            unit = Decimal(str(level_price))
        except Exception:
            unit = Decimal('0')
    else:
        # Fallback to base
        base = item_price.get('base')
        if base is not None and base != '':
            try:
                unit = Decimal(str(base))
            except Exception:
                unit = Decimal('0')
        else:
            return Decimal('0')

    # Apply quantity breaks if defined
    qty_breaks = item_price.get('qty_breaks')
    if isinstance(qty_breaks, list) and qty_breaks:
        # qty_breaks sorted by min_qty ascending
        # Find the highest break where quantity >= min_qty
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(quantity) >= float(min_qty):
                    break_price = brk.get('unit_price')
                    if break_price is not None:
                        return Decimal(str(break_price))
                    # variant_item_id breaks are not resolved here —
                    # caller must look up the variant item separately
                    break
            except (TypeError, ValueError):
                continue

    return unit


def get_price_for_line(
    item,
    customer=None,
    header_price_level: Optional[str] = None,
    line_price_level: Optional[str] = None,
    quantity: float = 1.0,
) -> Dict[str, Any]:
    """Full price resolution for an order/invoice line.

    Args:
        item: Item model instance (or dict with 'price' key)
        customer: OrgBase instance (or dict with 'price_level' key), optional
        header_price_level: Transaction header's price_level, optional
        line_price_level: Line-level override, optional
        quantity: Order quantity for break calculation

    Returns:
        Dict with resolved_level, unit_price, extended (unit * qty),
        and the fallback chain for transparency.
    """
    # Extract price dict from item
    if hasattr(item, 'price'):
        item_price = getattr(item, 'price', {}) or {}
    elif isinstance(item, dict):
        item_price = item.get('price', {}) or {}
    else:
        item_price = {}

    # Extract customer level
    customer_level = None
    if customer:
        if hasattr(customer, 'price_level'):
            customer_level = getattr(customer, 'price_level', None)
        elif isinstance(customer, dict):
            customer_level = customer.get('price_level')

    # Resolve level
    effective_level = resolve_price_level(
        customer_level=customer_level,
        header_level=header_price_level,
        line_level=line_price_level,
    )

    # Resolve price
    unit_price = resolve_unit_price(item_price, effective_level, quantity)
    extended = unit_price * Decimal(str(quantity))

    return {
        'price_level': effective_level,
        'unit_price': float(unit_price),
        'extended': float(extended),
        'quantity': quantity,
        'chain': {
            'line': line_price_level or None,
            'header': header_price_level or None,
            'customer': customer_level or None,
            'resolved': effective_level,
        },
    }
