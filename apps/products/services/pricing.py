"""Price resolution service.

Resolves the correct unit price for an item based on price level and quantity.

Resolution chain (resolve_price):
  1. OrgItem contract price (price_override in data JSON)
  2. Customer price_level on the item
  3. Explicit price_level parameter
  4. Item base price
  5. Fallback — 0

Within the resolved level, quantity breaks apply if defined.
Margin floor enforcement via Setting 'pricing_config'.

Legacy resolution chain (resolve_price_level):
  1. line.price_level (user override — requires authority)
  2. header.price_level (inherited from customer at order creation)
  3. customer.price_level (org default)
  4. 'base' (system fallback)
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

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


# ---------------------------------------------------------------------------
# Pricing configuration (from Setting 'pricing_config')
# ---------------------------------------------------------------------------

def _get_pricing_config() -> Dict[str, Any]:
    """Load pricing_config Setting. Returns defaults if not found."""
    defaults = {
        'minimum_margin_pct': 15,
        'default_price_level': 'base',
        'allow_below_cost': False,
        'require_margin_override_reason': True,
    }
    try:
        from apps.core.models.setting import Setting
        setting = Setting.objects.filter(
            name='pricing_config', is_active=True, is_deleted=False,
        ).first()
        if setting and isinstance(setting.config, dict):
            merged = dict(defaults)
            merged.update(setting.config)
            return merged
    except Exception:
        logger.warning("Could not load pricing_config Setting, using defaults")
    return defaults


# ---------------------------------------------------------------------------
# resolve_price — full resolution chain with contract, qty breaks, margin
# ---------------------------------------------------------------------------

def resolve_price(
    item_id: int,
    customer_id: Optional[int] = None,
    qty: int = 1,
    price_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve the effective unit price for an item.

    Resolution chain (first non-empty wins):
      1. OrgItem contract price_override (customer-specific)
      2. Customer's price_level on the item
      3. Explicit price_level parameter
      4. Item base price
      5. Fallback — 0

    After level resolution, quantity breaks are applied.
    Then margin floor is enforced via pricing_config Setting.

    Returns dict with: unit_price, price_level_used, qty_break_applied,
    below_margin_floor, margin_pct, cost, source.
    """
    from django.apps import apps as dj_apps

    Item = dj_apps.get_model('products', 'Item')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        raise ValueError(f"Item #{item_id} not found")

    item_price = item.price if isinstance(item.price, dict) else {}
    item_cost = item.cost if isinstance(item.cost, dict) else {}
    config = _get_pricing_config()

    resolved_price = Decimal('0')
    source = 'fallback'
    level_used = None
    qty_break_applied = None

    # ── Step 1: OrgItem contract price ─────────────────────────────────
    if customer_id:
        try:
            OrgItem = dj_apps.get_model('products', 'OrgItem')
            org_item = OrgItem.objects.filter(
                orgbase_id=customer_id, item_id=item_id,
            ).first()
            if org_item and isinstance(org_item.config, dict):
                override = org_item.config.get('price_override')
                if override is not None and override != '':
                    try:
                        resolved_price = Decimal(str(override))
                        source = 'contract'
                    except Exception:
                        pass
        except Exception:
            pass

    # ── Step 2: Customer price_level ───────────────────────────────────
    if source == 'fallback' and customer_id:
        try:
            OrgBase = dj_apps.get_model('orgs', 'OrgBase')
            customer = OrgBase.objects.filter(pk=customer_id).first()
            if customer:
                cust_level = getattr(customer, 'price_level', None)
                if cust_level and cust_level.strip():
                    cust_level = cust_level.strip().lower()
                    level_val = item_price.get(cust_level)
                    if level_val is not None and level_val != '':
                        try:
                            resolved_price = Decimal(str(level_val))
                            source = 'customer_level'
                            level_used = cust_level
                        except Exception:
                            pass
        except Exception:
            pass

    # ── Step 3: Explicit price_level param ─────────────────────────────
    if source == 'fallback' and price_level:
        cleaned = price_level.strip().lower()
        level_val = item_price.get(cleaned)
        if level_val is not None and level_val != '':
            try:
                resolved_price = Decimal(str(level_val))
                source = 'explicit_level'
                level_used = cleaned
            except Exception:
                pass

    # ── Step 4: Item base price ────────────────────────────────────────
    if source == 'fallback':
        base_val = item_price.get('base')
        if base_val is not None and base_val != '':
            try:
                resolved_price = Decimal(str(base_val))
                source = 'base'
                level_used = 'base'
            except Exception:
                pass

    # ── Quantity breaks ────────────────────────────────────────────────
    qty_breaks = item_price.get('qty_breaks')
    if isinstance(qty_breaks, list) and qty_breaks:
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(qty) >= float(min_qty):
                    break_price = brk.get('unit_price')
                    if break_price is not None:
                        resolved_price = Decimal(str(break_price))
                        qty_break_applied = {'min_qty': min_qty, 'unit_price': float(break_price)}
                        source = f"{source}+qty_break"
                        break
                    # variant_item_id break — look up that item's base price
                    variant_id = brk.get('variant_item_id')
                    if variant_id is not None:
                        try:
                            variant_item = Item.objects.only('price').get(pk=variant_id)
                            v_price = variant_item.price if isinstance(variant_item.price, dict) else {}
                            v_base = v_price.get('base')
                            if v_base is not None:
                                resolved_price = Decimal(str(v_base))
                                qty_break_applied = {'min_qty': min_qty, 'variant_item_id': variant_id}
                                source = f"{source}+variant_break"
                        except Item.DoesNotExist:
                            pass
                    break
            except (TypeError, ValueError):
                continue

    # ── Margin floor ───────────────────────────────────────────────────
    cost_value = Decimal('0')
    for cost_key in ('standard', 'avg', 'last'):
        cv = item_cost.get(cost_key)
        if cv is not None and cv != '':
            try:
                cost_value = Decimal(str(cv))
                break
            except Exception:
                continue

    below_margin_floor = False
    margin_pct = None
    min_margin = Decimal(str(config.get('minimum_margin_pct', 15)))

    if cost_value > 0 and resolved_price > 0:
        margin_pct = float(((resolved_price - cost_value) / resolved_price) * 100)
        floor_price = cost_value / (1 - min_margin / 100)
        if resolved_price < floor_price and not config.get('allow_below_cost', False):
            below_margin_floor = True
            resolved_price = floor_price.quantize(Decimal('0.01'))
            margin_pct = float(min_margin)
            source = f"{source}+margin_floor"
    elif cost_value > 0 and resolved_price > 0:
        margin_pct = float(((resolved_price - cost_value) / resolved_price) * 100)

    return {
        'unit_price': float(resolved_price),
        'price_level_used': level_used,
        'qty_break_applied': qty_break_applied,
        'below_margin_floor': below_margin_floor,
        'margin_pct': margin_pct,
        'cost': float(cost_value),
        'source': source,
    }


# ---------------------------------------------------------------------------
# get_price_matrix — full pricing grid for UI display
# ---------------------------------------------------------------------------

def get_price_matrix(item_id: int) -> Dict[str, Any]:
    """Return all price levels and qty breaks for an item.

    Used by the UI to show the full pricing grid.
    """
    from django.apps import apps as dj_apps
    Item = dj_apps.get_model('products', 'Item')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        raise ValueError(f"Item #{item_id} not found")

    item_price = item.price if isinstance(item.price, dict) else {}
    item_cost = item.cost if isinstance(item.cost, dict) else {}

    # Build levels dict
    levels: Dict[str, Optional[float]] = {}
    for lvl in VALID_PRICE_LEVELS:
        val = item_price.get(lvl)
        if val is not None and val != '':
            try:
                levels[lvl] = float(Decimal(str(val)))
            except Exception:
                levels[lvl] = None
        else:
            levels[lvl] = None

    # Qty breaks
    qty_breaks = item_price.get('qty_breaks', [])
    if not isinstance(qty_breaks, list):
        qty_breaks = []

    # Cost info
    cost_info: Dict[str, Optional[float]] = {}
    for ck in ('standard', 'avg', 'last', 'landed'):
        cv = item_cost.get(ck)
        if cv is not None and cv != '':
            try:
                cost_info[ck] = float(Decimal(str(cv)))
            except Exception:
                cost_info[ck] = None
        else:
            cost_info[ck] = None

    return {
        'item_id': item_id,
        'item_name': str(item),
        'currency': item_price.get('currency', 'USD'),
        'levels': levels,
        'qty_breaks': qty_breaks,
        'cost': cost_info,
    }


# ---------------------------------------------------------------------------
# apply_line_pricing — resolve price for a transaction line and update it
# ---------------------------------------------------------------------------

def apply_line_pricing(
    line_model_name: str,
    line_id: int,
    customer_id: Optional[int] = None,
    qty: Optional[int] = None,
) -> Dict[str, Any]:
    """Resolve price for a specific transaction line and update it.

    Reads item from line.item_fk_id, qty from line.quantity.active,
    customer from parent transaction. Updates line.price.unit and
    line.price.extended. Returns the pricing result.
    """
    from django.apps import apps as dj_apps
    from apps.core.constants.model_registry import get_model_meta

    # Resolve line model
    meta = get_model_meta(line_model_name)
    if not meta:
        raise ValueError(f"Unknown line model: {line_model_name}")

    LineModel = meta.import_model()

    try:
        line = LineModel.objects.get(pk=line_id)
    except LineModel.DoesNotExist:
        raise ValueError(f"{line_model_name} #{line_id} not found")

    # Get item_id from line
    item_id = getattr(line, 'item_fk_id', None)
    if not item_id:
        # Try from item JSON
        item_json = getattr(line, 'item', None) or {}
        item_id = item_json.get('item_id')
    if not item_id:
        raise ValueError(f"Line #{line_id} has no item reference")

    # Get quantity
    if qty is None:
        line_qty = getattr(line, 'quantity', None) or {}
        qty = line_qty.get('active', 1) or 1
    qty = int(qty) if qty else 1

    # Get customer_id from parent if not provided
    if customer_id is None:
        parent = getattr(line, 'parent', None)
        if parent:
            customer_id = getattr(parent, 'customer_id', None)

    # Resolve price
    result = resolve_price(
        item_id=item_id,
        customer_id=customer_id,
        qty=qty,
        price_level=getattr(line, 'price_level', None),
    )

    # Update line price envelope
    if not isinstance(line.price, dict):
        line.price = {}
    line.price['unit'] = result['unit_price']
    line.price['extended'] = float(Decimal(str(result['unit_price'])) * Decimal(str(qty)))

    line.save(update_fields=['price'])

    result['line_id'] = line_id
    result['quantity'] = qty
    result['extended'] = line.price['extended']
    return result
