"""Price resolver — single function that returns the correct price for any line.

Cascade (first match wins, no stacking):
  1. price_locked (manual override on the line — skip everything)
  2. OrgItem (contact + item negotiated price)
  3. Catalog rule match (scope + applies_to + date window, highest priority)
     a. Universal % (blanket promo on all items)
     b. CatalogLine match by scope (item, category, vendor)
     c. Qty-break within a matching CatalogLine
  4. Contact price level (wholesale/distributor/retail tier)
  5. Item base price (fallback)

Returns a PriceResolution with full audit trail — which step resolved, catalog_id, discount.
Below margin_floor triggers an Action for approval.

Source: WC2 CalcDiscountedPrice, DscntSetPrice, OrdSetDiscount patterns.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.db.models import Q
from django.utils import timezone


@dataclass
class PriceResolution:
    """The result of resolving a price — carries full audit trail."""
    price: Decimal                      # final unit price
    base_price: Decimal                 # item's base price before adjustments
    discount_pct: Decimal               # total discount applied (0 if none)
    discount_amount: Decimal            # dollar amount of discount
    resolved_by: str                    # which cascade step determined the price
    catalog_id: Optional[int] = None    # catalog that matched (if any)
    catalog_name: str = ''              # human-readable catalog name
    catalog_line_id: Optional[int] = None
    org_item_id: Optional[int] = None   # OrgItem that matched (if any)
    price_level: str = ''               # price level used (if any)
    margin_pct: Optional[Decimal] = None
    below_margin_floor: bool = False    # true = needs approval
    margin_floor: Decimal = Decimal('0')
    price_locked: bool = False          # was this a manual override?


def resolve_price(
    item_id: int,
    *,
    contact_id: Optional[int] = None,
    qty: Decimal = Decimal('1'),
    date_ms: Optional[int] = None,
    price_locked_value: Optional[Decimal] = None,
) -> PriceResolution:
    """Resolve the correct price for an item+contact+qty combination.

    This is the single entry point for all pricing decisions.
    """
    from apps.products.models.item import Item
    from apps.products.models.catalog import Catalog, CatalogLine

    item = Item.objects.get(id=item_id)
    now_ms = date_ms or int(timezone.now().timestamp() * 1000)

    # Item base price
    price_data = item.price if isinstance(item.price, dict) else {}
    base_price = Decimal(str(price_data.get('base') or price_data.get('retail') or 0))
    cost_avg = Decimal(str((item.cost or {}).get('avg', 0) or 0))

    # --- Step 1: Manual override ---
    if price_locked_value is not None:
        return _build_result(price_locked_value, base_price, cost_avg, 'price_locked',
                             price_locked=True)

    # --- Step 2: OrgItem (contact + item negotiated price) ---
    if contact_id:
        org_item_price = _check_org_item(item_id, contact_id)
        if org_item_price is not None:
            return _build_result(org_item_price['price'], base_price, cost_avg, 'org_item',
                                 org_item_id=org_item_price['org_item_id'])

    # --- Step 3: Catalog rules ---
    catalog_result = _check_catalogs(item, contact_id, qty, now_ms, base_price)
    if catalog_result is not None:
        result = _build_result(catalog_result['price'], base_price, cost_avg, catalog_result['resolved_by'],
                               catalog_id=catalog_result.get('catalog_id'),
                               catalog_name=catalog_result.get('catalog_name', ''),
                               catalog_line_id=catalog_result.get('catalog_line_id'),
                               discount_pct=catalog_result.get('discount_pct', Decimal('0')))
        # Check margin floor
        if catalog_result.get('margin_floor') and result.margin_pct is not None:
            if result.margin_pct < catalog_result['margin_floor']:
                result.below_margin_floor = True
                result.margin_floor = catalog_result['margin_floor']
                _create_margin_approval(item, result, contact_id)
        return result

    # --- Step 4: Contact price level ---
    if contact_id:
        level_price = _check_contact_price_level(item, contact_id, price_data)
        if level_price is not None:
            return _build_result(level_price['price'], base_price, cost_avg, 'contact_price_level',
                                 price_level=level_price['level'])

    # --- Step 5: Item base price (fallback) ---
    return _build_result(base_price, base_price, cost_avg, 'base_price')


# ---------------------------------------------------------------------------
# Cascade helpers
# ---------------------------------------------------------------------------

def _check_org_item(item_id: int, contact_id: int) -> Optional[dict]:
    """Check OrgItem for a negotiated price."""
    try:
        from apps.products.models.org_item import OrgItem
        org_item = OrgItem.objects.filter(item_id=item_id, org_id=contact_id).first()
        if org_item and org_item.price_unit and org_item.price_unit > 0:
            return {'price': Decimal(str(org_item.price_unit)), 'org_item_id': org_item.id}
    except Exception:
        pass
    return None


def _check_catalogs(item, contact_id, qty, now_ms, base_price) -> Optional[dict]:
    """Check active catalogs for matching rules. Highest priority wins."""
    from apps.products.models.catalog import Catalog, CatalogLine

    # Find active catalogs within date window
    catalogs = Catalog.objects.filter(
        is_active=True,
        dt_effective_start__lte=now_ms,
    ).filter(
        Q(dt_effective_end__isnull=True) | Q(dt_effective_end__gte=now_ms)
    ).order_by('-priority')

    for catalog in catalogs:
        # Check if catalog applies to this contact
        if not _catalog_applies_to_contact(catalog, contact_id):
            continue

        # Universal % mode
        if catalog.is_universal_pct and catalog.universal_pct:
            pct = Decimal(str(catalog.universal_pct))
            price = (base_price * (Decimal('100') - pct) / Decimal('100')).quantize(Decimal('0.01'))
            return {
                'price': price,
                'resolved_by': 'catalog_universal_pct',
                'catalog_id': catalog.id,
                'catalog_name': catalog.name,
                'discount_pct': pct,
                'margin_floor': Decimal(str(catalog.margin_floor)) if catalog.margin_floor else None,
            }

        # Per-line rules
        line = _find_matching_catalog_line(catalog, item, qty)
        if line:
            price = _apply_catalog_line(line, base_price, qty)
            return {
                'price': price,
                'resolved_by': 'catalog_line',
                'catalog_id': catalog.id,
                'catalog_name': catalog.name,
                'catalog_line_id': line.id,
                'discount_pct': Decimal(str(line.discount_percent or line.adjustment_value or 0)),
                'margin_floor': Decimal(str(catalog.margin_floor)) if catalog.margin_floor else None,
            }

    return None


def _catalog_applies_to_contact(catalog, contact_id) -> bool:
    """Check if a catalog's applies_to scope includes this contact."""
    applies = catalog.applies_to if isinstance(catalog.applies_to, dict) else {}

    # If applies_to is empty or all=true, catalog applies to everyone
    if not applies or applies.get('all', False):
        return True

    # Check specific contact IDs
    contact_ids = applies.get('contacts', [])
    if contact_id and contact_id in contact_ids:
        return True

    # Check contact types (requires DB lookup)
    contact_types = applies.get('contact_types', [])
    if contact_types and contact_id:
        try:
            from apps.core.models.contact import Contact
            contact = Contact.objects.filter(id=contact_id).values_list('metadata', flat=True).first()
            if isinstance(contact, dict):
                ctype = contact.get('customer_type', '')
                if ctype in contact_types:
                    return True
        except Exception:
            pass

    # Check by customer org FK on catalog
    if catalog.customer_orgbase_id and contact_id:
        try:
            from apps.orgs.models.base import OrgBase
            org = OrgBase.objects.filter(contacts__id=contact_id, id=catalog.customer_orgbase_id).exists()
            if org:
                return True
        except Exception:
            pass

    return False


def _find_matching_catalog_line(catalog, item, qty):
    """Find the best matching CatalogLine for an item within a catalog."""
    from apps.products.models.catalog import CatalogLine

    # Direct item match first
    line = CatalogLine.objects.filter(catalog=catalog, item=item).first()
    if line and _qty_in_range(line, qty):
        return line

    # Scope-based match (category, vendor, all_items)
    lines = CatalogLine.objects.filter(catalog=catalog, item__isnull=True).order_by('id')
    for line in lines:
        scope = line.scope if isinstance(line.scope, dict) else {}
        if scope.get('all_items', False) and _qty_in_range(line, qty):
            return line
        # Check category match
        categories = scope.get('categories', [])
        if categories:
            item_cats = (item.catalog or {}).get('categories', []) if isinstance(item.catalog, dict) else []
            if any(c in categories for c in item_cats) and _qty_in_range(line, qty):
                return line
        # Check vendor match
        vendors = scope.get('vendors', [])
        if vendors and item.vendor_id and item.vendor_id in vendors and _qty_in_range(line, qty):
            return line

    return None


def _qty_in_range(line, qty) -> bool:
    """Check if qty falls within a CatalogLine's min/max range."""
    if line.min_qty is not None and qty < line.min_qty:
        return False
    if line.max_qty is not None and qty > line.max_qty:
        return False
    return True


def _apply_catalog_line(line, base_price, qty) -> Decimal:
    """Apply a CatalogLine's adjustment to the base price."""
    adj_type = line.adjustment_type or 'percent_off'
    adj_value = Decimal(str(line.adjustment_value or 0))

    if adj_type == 'fixed_price':
        return Decimal(str(line.price_unit or adj_value))
    elif adj_type == 'percent_off':
        pct = Decimal(str(line.discount_percent or adj_value or 0))
        return (base_price * (Decimal('100') - pct) / Decimal('100')).quantize(Decimal('0.01'))
    elif adj_type == 'amount_off':
        amt = Decimal(str(line.discount_amount or adj_value or 0))
        return max(Decimal('0'), base_price - amt)
    elif adj_type == 'price_level':
        # adj_value names the level: 'wholesale', 'distributor', etc.
        # Handled by _check_contact_price_level pattern
        return base_price

    return base_price


def _check_contact_price_level(item, contact_id, price_data) -> Optional[dict]:
    """Check if the contact has a price level that maps to an item price tier."""
    try:
        from apps.core.models.contact import Contact
        contact = Contact.objects.filter(id=contact_id).first()
        if not contact:
            return None

        # Get price level from contact metadata or prefs
        meta = contact.metadata if isinstance(contact.metadata, dict) else {}
        level = meta.get('price_level', '')

        if not level:
            prefs = contact.prefs if isinstance(contact.prefs, dict) else {}
            level = prefs.get('price_level', '')

        if not level:
            return None

        # Map level to item price
        level_lower = level.lower()
        tiers = price_data.get('tiers', [])
        for tier in tiers:
            if isinstance(tier, dict) and tier.get('level', '').lower() == level_lower:
                tier_price = tier.get('price')
                if tier_price is not None:
                    return {'price': Decimal(str(tier_price)), 'level': level}

        # Check named price fields
        level_map = {'wholesale': 'wholesale', 'distributor': 'distributor',
                     'retail': 'retail', 'sample': 'sample', 'msrp': 'msrp'}
        field = level_map.get(level_lower)
        if field and price_data.get(field):
            return {'price': Decimal(str(price_data[field])), 'level': level}

    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Result builder + margin check
# ---------------------------------------------------------------------------

def _build_result(
    price: Decimal,
    base_price: Decimal,
    cost_avg: Decimal,
    resolved_by: str,
    **kwargs,
) -> PriceResolution:
    """Build a PriceResolution with computed margin and discount."""
    discount_pct = kwargs.pop('discount_pct', Decimal('0'))
    discount_amount = base_price - price if base_price > 0 else Decimal('0')

    margin_pct = None
    if cost_avg > 0:
        margin_pct = ((price - cost_avg) / cost_avg * Decimal('100')).quantize(Decimal('0.01'))

    return PriceResolution(
        price=price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        base_price=base_price,
        discount_pct=discount_pct,
        discount_amount=max(Decimal('0'), discount_amount),
        resolved_by=resolved_by,
        margin_pct=margin_pct,
        **kwargs,
    )


def _create_margin_approval(item, result: PriceResolution, contact_id: Optional[int]):
    """Create an informational Action when price falls below margin floor.

    Does NOT block shipment — flag and ship, review in the sales dashboard.
    """
    try:
        from apps.core.models.action import Action
        Action.objects.create(
            title=f'Below-margin price: {item.ida or item.name}',
            description=(
                f'{item.ida} priced at ${result.price} produces {result.margin_pct}% margin, '
                f'below floor of {result.margin_floor}%. '
                f'Catalog: {result.catalog_name} (#{result.catalog_id}). '
                f'Contact: #{contact_id}. Review in sales dashboard.'
            ),
            status='Backlog',
            priority='low',
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Legacy price helpers (merged from pricing.py)
# ---------------------------------------------------------------------------

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
    item_price: dict,
    price_level: str,
    quantity: float = 1.0,
) -> Decimal:
    """Resolve the unit price for an item at a given level and quantity.

    Args:
        item_price: The Item.price JSON dict (has keys: base, retail, wholesale, etc.)
        price_level: Resolved price level key (from resolve_price_level)
        quantity: Order quantity — used for quantity break lookup

    Returns:
        Decimal unit price. Falls back through: level -> base -> 0.
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
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(quantity) >= float(min_qty):
                    level_price = brk.get(price_level)
                    if level_price is not None and level_price != '':
                        return Decimal(str(level_price))
                    level_pct_key = f'{price_level}_pct'
                    level_pct = brk.get(level_pct_key)
                    if level_pct is not None:
                        break_base = brk.get('base')
                        if break_base is None:
                            break_base = item_price.get('base', 0)
                        if break_base:
                            return Decimal(str(break_base)) * (1 - Decimal(str(level_pct)) / 100)
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
) -> dict:
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
    if hasattr(item, 'price'):
        item_price = getattr(item, 'price', {}) or {}
    elif isinstance(item, dict):
        item_price = item.get('price', {}) or {}
    else:
        item_price = {}

    customer_level = None
    if customer:
        if hasattr(customer, 'price_level'):
            customer_level = getattr(customer, 'price_level', None)
        elif isinstance(customer, dict):
            customer_level = customer.get('price_level')

    effective_level = resolve_price_level(
        customer_level=customer_level,
        header_level=header_price_level,
        line_level=line_price_level,
    )

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


def _legacy_resolve_catalog_price(
    item_id: int,
    customer_id: int,
    qty: int = 1,
) -> Optional[dict]:
    """Check if this item has special catalog pricing for this customer.

    Legacy helper — finds active catalogs that contain this item, apply to this
    customer, and are within their effective date range. Highest priority wins.
    """
    import time
    from django.apps import apps as dj_apps
    from django.db import models as dj_models

    now_ms = int(time.time() * 1000)
    CatalogLine = dj_apps.get_model('products', 'CatalogLine')

    lines = CatalogLine.objects.filter(
        item_id=item_id,
        catalog__is_active=True,
        catalog__dt_effective_start__lte=now_ms,
    ).filter(
        dj_models.Q(catalog__dt_effective_end__isnull=True) |
        dj_models.Q(catalog__dt_effective_end__gte=now_ms)
    ).select_related('catalog').order_by('-catalog__priority')

    for cl in lines:
        catalog = cl.catalog
        if not _legacy_catalog_applies_to_customer(catalog, customer_id):
            continue
        price = _legacy_get_catalog_line_price(cl, qty)
        if price is not None:
            return {
                'price': price,
                'catalog_id': catalog.pk,
                'catalog_name': catalog.name,
                'level': f'catalog:{catalog.code}',
                'qty_break': None,
            }

    Catalog = dj_apps.get_model('products', 'Catalog')
    universal_catalogs = Catalog.objects.filter(
        is_active=True,
        is_universal_pct=True,
        universal_pct__gt=0,
        dt_effective_start__lte=now_ms,
    ).filter(
        dj_models.Q(dt_effective_end__isnull=True) |
        dj_models.Q(dt_effective_end__gte=now_ms)
    ).order_by('-priority')

    for catalog in universal_catalogs:
        if not _legacy_catalog_applies_to_customer(catalog, customer_id):
            continue
        return {
            'price': None,
            'universal_pct': float(catalog.universal_pct),
            'catalog_id': catalog.pk,
            'catalog_name': catalog.name,
            'level': f'catalog:{catalog.code}',
            'qty_break': None,
        }

    return None


def _legacy_catalog_applies_to_customer(catalog, customer_id: int) -> bool:
    """Check if a catalog's scope includes this customer (legacy helper)."""
    if catalog.customer_orgbase_id and catalog.customer_orgbase_id == customer_id:
        return True

    applies_to = catalog.applies_to if isinstance(catalog.applies_to, dict) else {}

    if not applies_to and not catalog.customer_orgbase_id:
        return True
    if applies_to.get('all'):
        return True

    contacts = applies_to.get('contacts', [])
    if isinstance(contacts, list) and customer_id in contacts:
        return True

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


def _legacy_get_catalog_line_price(cl, qty: int = 1) -> Optional[Decimal]:
    """Extract the effective price from a CatalogLine for a quantity (legacy helper)."""
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

    if cl.price_unit is not None:
        base = Decimal(str(cl.price_unit))
        if cl.discount_percent and cl.discount_percent > 0:
            base = base * (1 - cl.discount_percent / 100)
        elif cl.discount_amount and cl.discount_amount > 0:
            base = base - cl.discount_amount
        return base.quantize(Decimal('0.01'))

    return None


def _legacy_get_pricing_config() -> dict:
    """Load pricing_config Setting (legacy helper). Returns defaults if not found."""
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
        import logging
        logging.getLogger(__name__).warning("Could not load pricing_config Setting, using defaults")
    return defaults


def resolve_price_legacy(
    item_id: int,
    customer_id: Optional[int] = None,
    qty: int = 1,
    price_level: Optional[str] = None,
) -> dict:
    """Legacy price resolution chain (from pricing.py).

    Resolution chain (first non-empty wins):
      1. OrgItem contract price_override (customer-specific)
      2. Customer's price_level on the item
      3. Explicit price_level parameter
      4. Item base price
      5. Fallback -- 0

    After level resolution, quantity breaks are applied.
    Then margin floor is enforced via pricing_config Setting.
    """
    from django.apps import apps as dj_apps

    Item = dj_apps.get_model('products', 'Item')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        raise ValueError(f"Item #{item_id} not found")

    item_price = item.price if isinstance(item.price, dict) else {}
    item_cost = item.cost if isinstance(item.cost, dict) else {}
    config = _legacy_get_pricing_config()

    resolved_price = Decimal('0')
    source = 'fallback'
    level_used = None
    qty_break_applied = None

    # Step 0: Catalog price
    catalog_universal_pct = None
    if customer_id:
        catalog_result = _legacy_resolve_catalog_price(item_id, customer_id, qty)
        if catalog_result:
            if catalog_result.get('price') is not None:
                resolved_price = catalog_result['price']
                source = 'catalog'
                level_used = catalog_result.get('level')
                qty_break_applied = catalog_result.get('qty_break')
            elif catalog_result.get('universal_pct'):
                catalog_universal_pct = Decimal(str(catalog_result['universal_pct']))

    # Step 1: OrgItem contract price
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

    # Step 2: Customer price_level
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

    # Step 3: Explicit price_level param
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

    # Step 4: Item base price
    if source == 'fallback':
        base_val = item_price.get('base')
        if base_val is not None and base_val != '':
            try:
                resolved_price = Decimal(str(base_val))
                source = 'base'
                level_used = 'base'
            except Exception:
                pass

    # Quantity breaks
    effective_level = level_used or 'base'
    qty_breaks = item_price.get('qty_breaks')
    if isinstance(qty_breaks, list) and qty_breaks:
        for brk in reversed(qty_breaks):
            if not isinstance(brk, dict):
                continue
            min_qty = brk.get('min_qty', 0)
            try:
                if float(qty) >= float(min_qty):
                    lp = brk.get(effective_level)
                    if lp is not None and lp != '':
                        resolved_price = Decimal(str(lp))
                        qty_break_applied = {'min_qty': min_qty, 'level': effective_level, 'unit_price': float(lp)}
                        source = f"{source}+qty_break"
                        break
                    level_pct = brk.get(f'{effective_level}_pct')
                    if level_pct is not None:
                        break_base = brk.get('base') or item_price.get('base', 0)
                        if break_base:
                            resolved_price = Decimal(str(break_base)) * (1 - Decimal(str(level_pct)) / 100)
                            qty_break_applied = {'min_qty': min_qty, 'level': effective_level, 'pct': float(level_pct)}
                            source = f"{source}+qty_break_pct"
                            break
                    generic = brk.get('unit_price')
                    if generic is not None:
                        resolved_price = Decimal(str(generic))
                        qty_break_applied = {'min_qty': min_qty, 'unit_price': float(generic)}
                        source = f"{source}+qty_break"
                        break
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

    # Universal catalog % discount
    if catalog_universal_pct and catalog_universal_pct > 0 and resolved_price > 0:
        resolved_price = resolved_price * (1 - catalog_universal_pct / 100)
        source = f"{source}+catalog_universal_{catalog_universal_pct}pct"

    # Margin floor
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

    return {
        'unit_price': float(resolved_price),
        'price_level_used': level_used,
        'qty_break_applied': qty_break_applied,
        'below_margin_floor': below_margin_floor,
        'margin_pct': margin_pct,
        'cost': float(cost_value),
        'source': source,
    }


def get_price_matrix(item_id: int) -> dict:
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

    levels: dict = {}
    for lvl in VALID_PRICE_LEVELS:
        val = item_price.get(lvl)
        if val is not None and val != '':
            try:
                levels[lvl] = float(Decimal(str(val)))
            except Exception:
                levels[lvl] = None
        else:
            levels[lvl] = None

    qty_breaks = item_price.get('qty_breaks', [])
    if not isinstance(qty_breaks, list):
        qty_breaks = []

    cost_info: dict = {}
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


def apply_line_pricing(
    line_model_name: str,
    line_id: int,
    customer_id: Optional[int] = None,
    qty: Optional[int] = None,
) -> dict:
    """Resolve price for a specific transaction line and update it.

    Reads item from line.item_fk_id, qty from line.quantity.active,
    customer from parent transaction. Updates line.price.unit and
    line.price.extended. Returns the pricing result.
    """
    from django.apps import apps as dj_apps
    from apps.core.constants.model_registry import get_model_meta

    meta = get_model_meta(line_model_name)
    if not meta:
        raise ValueError(f"Unknown line model: {line_model_name}")

    LineModel = meta.import_model()

    try:
        line = LineModel.objects.get(pk=line_id)
    except LineModel.DoesNotExist:
        raise ValueError(f"{line_model_name} #{line_id} not found")

    item_id = getattr(line, 'item_fk_id', None)
    if not item_id:
        item_json = getattr(line, 'item', None) or {}
        item_id = item_json.get('item_id')
    if not item_id:
        raise ValueError(f"Line #{line_id} has no item reference")

    if qty is None:
        line_qty = getattr(line, 'quantity', None) or {}
        qty = line_qty.get('active', 1) or 1
    qty = int(qty) if qty else 1

    if customer_id is None:
        parent = getattr(line, 'parent', None)
        if parent:
            customer_id = getattr(parent, 'customer_id', None)

    result = resolve_price_legacy(
        item_id=item_id,
        customer_id=customer_id,
        qty=qty,
        price_level=getattr(line, 'price_level', None),
    )

    if not isinstance(line.price, dict):
        line.price = {}
    line.price['unit'] = result['unit_price']
    line.price['extended'] = float(Decimal(str(result['unit_price'])) * Decimal(str(qty)))

    line.save(update_fields=['price'])

    result['line_id'] = line_id
    result['quantity'] = qty
    result['extended'] = line.price['extended']
    return result


__all__ = [
    'resolve_price', 'PriceResolution',
    'resolve_price_level', 'resolve_unit_price', 'get_price_for_line',
    'get_price_matrix', 'apply_line_pricing', 'resolve_price_legacy',
]
