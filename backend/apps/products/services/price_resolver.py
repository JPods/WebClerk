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


__all__ = ['resolve_price', 'PriceResolution']
