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

from django.db import models

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
    # Each break can carry per-level dollar prices and/or percentages:
    #   {"min_qty": 25, "max_qty": 99, "base": 14.00, "retail": 11.00,
    #    "wholesale": 9.00, "wholesale_pct": 33.3}
    # Dollar price wins. Percentage calculates from the break's base (or item base).
    qty_breaks = item_price.get('qty_breaks')
    if isinstance(qty_breaks, list) and qty_breaks:
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(quantity) >= float(min_qty):
                    # Try level-specific dollar price first
                    level_price = brk.get(price_level)
                    if level_price is not None and level_price != '':
                        return Decimal(str(level_price))
                    # Try level-specific percentage (off break's base or item base)
                    level_pct_key = f'{price_level}_pct'
                    level_pct = brk.get(level_pct_key)
                    if level_pct is not None:
                        break_base = brk.get('base')
                        if break_base is None:
                            break_base = item_price.get('base', 0)
                        if break_base:
                            return Decimal(str(break_base)) * (1 - Decimal(str(level_pct)) / 100)
                    # Fall back to generic unit_price (legacy format)
                    generic = brk.get('unit_price')
                    if generic is not None:
                        return Decimal(str(generic))
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
# Catalog price resolution
# ---------------------------------------------------------------------------

def _resolve_catalog_price(
    item_id: int,
    customer_id: int,
    qty: int = 1,
) -> Optional[Dict[str, Any]]:
    """Check if this item has special catalog pricing for this customer.

    Finds active catalogs that:
      - Contain this item (via CatalogLine)
      - Apply to this customer (via applies_to scope or customer_orgbase FK)
      - Are within their effective date range
    Highest priority catalog wins.

    Returns dict with price, level, catalog info — or None if no catalog applies.
    """
    import time
    from django.apps import apps as dj_apps

    now_ms = int(time.time() * 1000)

    CatalogLine = dj_apps.get_model('products', 'CatalogLine')

    # Find catalog lines for this item in active, current catalogs
    lines = CatalogLine.objects.filter(
        item_id=item_id,
        catalog__is_active=True,
        catalog__dt_effective_start__lte=now_ms,
    ).filter(
        models.Q(catalog__dt_effective_end__isnull=True) |
        models.Q(catalog__dt_effective_end__gte=now_ms)
    ).select_related('catalog').order_by('-catalog__priority')

    for cl in lines:
        catalog = cl.catalog

        # Check if this catalog applies to this customer
        if not _catalog_applies_to_customer(catalog, customer_id):
            continue

        # Resolve price from the catalog line
        price = _get_catalog_line_price(cl, qty)
        if price is not None:
            return {
                'price': price,
                'catalog_id': catalog.pk,
                'catalog_name': catalog.name,
                'level': f'catalog:{catalog.code}',
                'qty_break': None,
            }

    # No item-specific catalog line found — check for universal % catalogs
    # These apply a blanket discount to ALL products for matching customers.
    Catalog = dj_apps.get_model('products', 'Catalog')
    universal_catalogs = Catalog.objects.filter(
        is_active=True,
        is_universal_pct=True,
        universal_pct__gt=0,
        dt_effective_start__lte=now_ms,
    ).filter(
        models.Q(dt_effective_end__isnull=True) |
        models.Q(dt_effective_end__gte=now_ms)
    ).order_by('-priority')

    for catalog in universal_catalogs:
        if not _catalog_applies_to_customer(catalog, customer_id):
            continue

        # Universal catalog applies — return the discount percentage.
        # Caller will apply it to whatever base price resolves from the
        # standard chain (price_level → base).
        return {
            'price': None,  # no fixed price — percentage discount
            'universal_pct': float(catalog.universal_pct),
            'catalog_id': catalog.pk,
            'catalog_name': catalog.name,
            'level': f'catalog:{catalog.code}',
            'qty_break': None,
        }

    return None


def _catalog_applies_to_customer(catalog, customer_id: int) -> bool:
    """Check if a catalog's scope includes this customer.

    Scope check:
      1. customer_orgbase FK matches directly
      2. applies_to.all = True (universal catalog)
      3. applies_to.contacts includes customer_id
      4. applies_to.contact_types includes customer's price_level/type
    No scope and no customer_orgbase = catalog applies to everyone.
    """
    # Direct FK match
    if catalog.customer_orgbase_id and catalog.customer_orgbase_id == customer_id:
        return True

    applies_to = catalog.applies_to if isinstance(catalog.applies_to, dict) else {}

    # No scope defined and no customer FK = applies to all
    if not applies_to and not catalog.customer_orgbase_id:
        return True

    # Explicit all flag
    if applies_to.get('all'):
        return True

    # Contact list
    contacts = applies_to.get('contacts', [])
    if isinstance(contacts, list) and customer_id in contacts:
        return True

    # Contact type match (e.g., 'wholesale' matches customer.price_level)
    contact_types = applies_to.get('contact_types', [])
    if isinstance(contact_types, list) and contact_types:
        try:
            from django.apps import apps as dj_apps
            OrgBase = dj_apps.get_model('orgs', 'OrgBase')
            customer = OrgBase.objects.filter(pk=customer_id).only('price_level').first()
            if customer and getattr(customer, 'price_level', '') in contact_types:
                return True
        except Exception:
            pass

    return False


def _get_catalog_line_price(cl, qty: int = 1) -> Optional[Decimal]:
    """Extract the effective price from a CatalogLine for a quantity.

    Checks:
      1. Quantity-based tiers in items.pricing.tiers
      2. CatalogLine.price_unit (flat catalog price)
      3. Discount applied to price_unit
    """
    # Check tiers first
    items_data = cl.items if isinstance(cl.items, dict) else {}
    pricing = items_data.get('pricing', {})
    tiers = pricing.get('tiers', [])
    if isinstance(tiers, list) and tiers:
        tiers_sorted = sorted(tiers, key=lambda t: t.get('min_qty', 0))
        tier_price = None
        for t in tiers_sorted:
            if qty >= (t.get('min_qty', 0) or 0):
                tp = t.get('price')
                if tp is not None:
                    tier_price = Decimal(str(tp))
        if tier_price is not None:
            return tier_price

    # Flat catalog price
    if cl.price_unit is not None:
        base = Decimal(str(cl.price_unit))
        # Apply discount if present
        if cl.discount_percent and cl.discount_percent > 0:
            base = base * (1 - cl.discount_percent / 100)
        elif cl.discount_amount and cl.discount_amount > 0:
            base = base - cl.discount_amount
        return base.quantize(Decimal('0.01'))

    return None


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

    # ── Step 0: Catalog price (highest priority) ─────────────────────
    # If the item is listed in an active catalog that applies to this
    # customer, the catalog price wins. Catalogs with higher priority
    # take precedence. This is the most common pricing path — vendors
    # publish catalogs with special pricing for their customers.
    #
    # Two catalog types:
    #   - Item-specific: CatalogLine with fixed price or tiers
    #   - Universal %: blanket discount on ALL products for this customer
    catalog_universal_pct = None
    if customer_id:
        catalog_result = _resolve_catalog_price(item_id, customer_id, qty)
        if catalog_result:
            if catalog_result.get('price') is not None:
                # Item-specific catalog price — use directly
                resolved_price = catalog_result['price']
                source = 'catalog'
                level_used = catalog_result.get('level')
                qty_break_applied = catalog_result.get('qty_break')
            elif catalog_result.get('universal_pct'):
                # Universal % catalog — apply after base price resolves
                catalog_universal_pct = Decimal(str(catalog_result['universal_pct']))
                # Don't set source yet — let the chain resolve base price first

    # ── Step 1: OrgItem contract price ─────────────────────────────────
    if source == 'fallback' and customer_id:
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
    # Each break row can have per-level dollar prices and percentages:
    #   {"min_qty": 25, "retail": 11.00, "wholesale_pct": 33.3, ...}
    # Dollar price wins. Percentage calculates off break's base or item base.
    effective_level = level_used or 'base'
    qty_breaks = item_price.get('qty_breaks')
    if isinstance(qty_breaks, list) and qty_breaks:
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(qty) >= float(min_qty):
                    # Level-specific dollar price
                    level_price = brk.get(effective_level)
                    if level_price is not None and level_price != '':
                        resolved_price = Decimal(str(level_price))
                        qty_break_applied = {'min_qty': min_qty, 'level': effective_level, 'unit_price': float(level_price)}
                        source = f"{source}+qty_break"
                        break
                    # Level-specific percentage
                    level_pct = brk.get(f'{effective_level}_pct')
                    if level_pct is not None:
                        break_base = brk.get('base') or item_price.get('base', 0)
                        if break_base:
                            resolved_price = Decimal(str(break_base)) * (1 - Decimal(str(level_pct)) / 100)
                            qty_break_applied = {'min_qty': min_qty, 'level': effective_level, 'pct': float(level_pct)}
                            source = f"{source}+qty_break_pct"
                            break
                    # Generic unit_price (legacy)
                    generic = brk.get('unit_price')
                    if generic is not None:
                        resolved_price = Decimal(str(generic))
                        qty_break_applied = {'min_qty': min_qty, 'unit_price': float(generic)}
                        source = f"{source}+qty_break"
                        break
                    # Variant item break
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

    # ── Universal catalog % discount ──────────────────────────────────
    # Applied after base price resolves, before margin check.
    # A catalog with is_universal_pct=True and universal_pct=15 means
    # "15% off whatever this customer's price_level price is."
    if catalog_universal_pct and catalog_universal_pct > 0 and resolved_price > 0:
        resolved_price = resolved_price * (1 - catalog_universal_pct / 100)
        source = f"{source}+catalog_universal_{catalog_universal_pct}pct"

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
        if resolved_price < floor_price:
            below_margin_floor = True
            # WARNING only — user is in control, system does not override price.
            # WC2 heritage: PriceBelowMargi warned but never blocked.
            # The flag 'below_margin_floor' is returned for UI to display a warning.

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
