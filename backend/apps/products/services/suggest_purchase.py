"""Suggest Purchase service — preferred vendor resolution and reorder suggestions.

When items drop below their reorder point (item.quantity.min),
this service identifies them, resolves the preferred vendor for each,
and groups the suggestions into draft purchase orders.

Resolution chain for preferred vendor:
  1. Item.vendor_id (direct FK on item record)
  2. ItemXRef where is_preferred=True and source='wholesaler'

All quantities, including the stocking pair (min = reorder point, max = order up to),
read from Item.quantity. OrgItem was removed 2026-09-18.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db.models import Q

logger = logging.getLogger(__name__)


def _get_models():
    """Lazy-load Django models to avoid import-time app registry issues."""
    Item = dj_apps.get_model('products', 'Item')
    ItemXRef = dj_apps.get_model('products', 'ItemXRef')
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Purchase = dj_apps.get_model('transactions', 'Purchase')
    PurchaseLine = dj_apps.get_model('transactions', 'PurchaseLine')
    return Item, ItemXRef, OrgBase, Purchase, PurchaseLine


def _safe_decimal(val) -> Decimal:
    """Coerce a value to Decimal, returning 0 on failure."""
    if val is None:
        return Decimal('0')
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal('0')


def _qty_value(quantity_json: dict, key: str) -> Decimal:
    """Extract a numeric value from an Item.quantity JSONB dict."""
    if not isinstance(quantity_json, dict):
        return Decimal('0')
    return _safe_decimal(quantity_json.get(key))


def _item_warehouse_ids(item) -> List[int]:
    """Warehouse ids an item is linked to through item.refs.links.warehouse."""
    refs = item.refs if isinstance(item.refs, dict) else {}
    ids = (refs.get('links') or {}).get('warehouse') or []
    if not isinstance(ids, list):
        ids = [ids]
    out = []
    for v in ids:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def get_preferred_vendor(item_id: int) -> Dict[str, Any]:
    """Resolve the preferred vendor for an item.

    Resolution chain:
      1. item.vendor_id (direct FK)
      2. ItemXRef where is_preferred=True and source='wholesaler'

    Returns:
        {vendor_id, vendor_name, vendor_ida, cost}
        or empty dict if no vendor found.
    """
    Item, ItemXRef, OrgBase, _, _ = _get_models()

    try:
        item = Item.objects.select_related('vendor').get(pk=item_id, is_active=True)
    except Item.DoesNotExist:
        return {}

    # --- Chain 1: item.vendor_id ---
    if item.vendor_id and item.vendor:
        cost_val = None
        if isinstance(item.cost, dict):
            cost_val = item.cost.get('unit') or item.cost.get('last') or item.cost.get('average')
        return {
            'vendor_id': item.vendor.pk,
            'vendor_name': item.vendor.company,
            'vendor_ida': getattr(item.vendor, 'ida', ''),
            'cost': float(cost_val) if cost_val is not None else None,
        }

    # --- Chain 2: ItemXRef preferred wholesaler ---
    xref = (
        ItemXRef.objects
        .filter(item_id=item_id, is_preferred=True, source='wholesaler', is_active=True)
        .first()
    )
    if xref and xref.source_id:
        try:
            vendor = OrgBase.objects.get(pk=xref.source_id)
        except OrgBase.DoesNotExist:
            vendor = None
        if vendor:
            cost_val = None
            if isinstance(xref.cost, dict):
                cost_val = xref.cost.get('unit') or xref.cost.get('last')
            return {
                'vendor_id': vendor.pk,
                'vendor_name': vendor.company,
                'vendor_ida': getattr(vendor, 'ida', ''),
                'cost': float(cost_val) if cost_val is not None else None,
            }

    return {}


def compute_velocity_reorder_point(item_id: int, months: int = 3) -> Optional[Decimal]:
    """Compute reorder point from lead time × monthly velocity (wc2 pattern).

    Formula: qtyMin = (lead_time_days / 30) × avg_monthly_usage

    Uses the most recent N months of ItemUsage data. Returns None if
    insufficient data (item needs a static reorder point instead).

    Args:
        item_id: Item PK
        months: number of months to average over (default 3)

    Returns:
        Computed reorder point as Decimal, or None if no usage data.
    """
    from django.apps import apps as dj_apps
    from datetime import datetime, timezone as tz

    Item = dj_apps.get_model('products', 'Item')
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return None

    # Get lead time from item record
    record = item.record if isinstance(item.record, dict) else {}
    lead_time_days = _safe_decimal(
        record.get('lead_time_days')
        or (item.cost or {}).get('lead_time_days')
        or 30
    )

    # Get monthly usage from ItemUsage model
    try:
        ItemUsage = dj_apps.get_model('products', 'ItemUsage')
    except LookupError:
        return None

    now = datetime.now(tz.utc)
    # Look back N months
    import calendar
    cutoff_month = now.month - months
    cutoff_year = now.year
    while cutoff_month < 1:
        cutoff_month += 12
        cutoff_year -= 1

    usages = ItemUsage.objects.filter(
        item_id=item_id,
        is_active=True,
    ).order_by('-dt_created')[:months]

    if not usages.exists():
        return None

    # Sum usage quantities
    total_qty = Decimal('0')
    count = 0
    for usage in usages:
        usage_data = usage.data if isinstance(usage.data, dict) else {}
        qty = _safe_decimal(
            usage_data.get('sales_qty')
            or usage_data.get('quantity_sold')
            or usage_data.get('qty')
        )
        total_qty += qty
        count += 1

    if count == 0 or total_qty <= 0:
        return None

    avg_monthly = total_qty / Decimal(str(count))
    reorder_point = (lead_time_days / Decimal('30')) * avg_monthly

    return reorder_point.quantize(Decimal('1'))


def get_items_below_reorder(warehouse_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Find items where on_hand or available is below the reorder point.

    The reorder point is item.quantity.min; the order-up-to level is item.quantity.max.

    Args:
        warehouse_id: optional Warehouse id — only items linked to it through
            item.refs.links.warehouse are considered.

    Returns:
        List of dicts with item details and vendor info.
    """
    Item, ItemXRef, OrgBase, _, _ = _get_models()

    items = (
        Item.objects
        .filter(is_active=True, is_deleted=False, quantity__min__gt=0)
        .select_related('vendor')
    )
    if warehouse_id:
        items = [i for i in items if warehouse_id in _item_warehouse_ids(i)]

    results = []
    for item in items:
        qty = item.quantity if isinstance(item.quantity, dict) else {}
        on_hand = _qty_value(qty, 'on_hand')
        available = _qty_value(qty, 'available')
        reorder_point = _qty_value(qty, 'min')

        # Check if below reorder point
        if on_hand >= reorder_point and available >= reorder_point:
            continue

        # Calculate reorder quantity
        reorder_max = _qty_value(qty, 'max')
        if reorder_max > 0:
            reorder_qty = reorder_max - on_hand
        else:
            reorder_qty = reorder_point * 2

        if reorder_qty <= 0:
            reorder_qty = reorder_point

        # Resolve preferred vendor
        vendor_info = get_preferred_vendor(item.pk)

        results.append({
            'item_id': item.pk,
            'item_ida': getattr(item, 'ida', ''),
            'item_name': item.name,
            'on_hand': float(on_hand),
            'available': float(available),
            'reorder_point': float(reorder_point),
            'reorder_qty': float(reorder_qty),
            'preferred_vendor_id': vendor_info.get('vendor_id'),
            'preferred_vendor_name': vendor_info.get('vendor_name'),
        })

    return results


def suggest_purchase_orders(warehouse_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Group items below reorder by preferred vendor into suggested purchase orders.

    Args:
        warehouse_id: optional OrgBase id to restrict to a specific warehouse.

    Returns:
        List of vendor groups, each with items and estimated totals.
    """
    items_below = get_items_below_reorder(warehouse_id)
    if not items_below:
        return []

    # Group by preferred vendor
    vendor_groups: Dict[Optional[int], List[Dict[str, Any]]] = {}
    for rec in items_below:
        vid = rec['preferred_vendor_id']
        vendor_groups.setdefault(vid, []).append(rec)

    # Resolve vendor costs where missing
    _, ItemXRef, _, _, _ = _get_models()

    suggestions = []
    for vid, items in vendor_groups.items():
        vendor_name = items[0].get('preferred_vendor_name') or f'Unknown (id={vid})'
        line_items = []
        estimated_total = Decimal('0')

        for rec in items:
            qty = Decimal(str(rec['reorder_qty']))
            # Try to get cost from vendor resolution
            vendor_info = get_preferred_vendor(rec['item_id'])
            unit_cost = _safe_decimal(vendor_info.get('cost'))
            est_cost = float(qty * unit_cost)
            estimated_total += Decimal(str(est_cost))

            line_items.append({
                'item_id': rec['item_id'],
                'item_ida': rec['item_ida'],
                'item_name': rec['item_name'],
                'qty': float(qty),
                'unit_cost': float(unit_cost),
                'estimated_cost': est_cost,
                'on_hand': rec['on_hand'],
                'reorder_point': rec['reorder_point'],
            })

        suggestions.append({
            'vendor_id': vid,
            'vendor_name': vendor_name,
            'items': line_items,
            'estimated_total': float(estimated_total),
        })

    # Sort by estimated total descending
    suggestions.sort(key=lambda s: s['estimated_total'], reverse=True)
    return suggestions


def create_draft_purchase(vendor_id: int, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create an actual Purchase record with status='planned' and PurchaseLines.

    Args:
        vendor_id: OrgBase id for the vendor.
        items: list of {item_id, qty, unit_cost (optional)}.

    Returns:
        Dict with purchase_id, line_count, and total.
    """
    Item, _, OrgBase, Purchase, PurchaseLine = _get_models()

    # Validate vendor
    try:
        vendor = OrgBase.objects.get(pk=vendor_id)
    except OrgBase.DoesNotExist:
        raise ValueError(f"Vendor {vendor_id} not found")

    # Create Purchase header
    purchase = Purchase(
        status='planned',
        vendor=vendor,
        metadata={'source': {'type': 'suggest_purchase', 'auto_generated': True}},
    )
    purchase.save()

    line_count = 0
    total_cost = Decimal('0')

    for entry in items:
        item_id = entry.get('item_id')
        qty = Decimal(str(entry.get('qty', 0)))
        unit_cost = _safe_decimal(entry.get('unit_cost'))

        if not item_id or qty <= 0:
            continue

        # Validate item exists
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            logger.warning("Item %s not found, skipping purchase line", item_id)
            continue

        # If no unit_cost provided, try to resolve from vendor info
        if unit_cost == 0:
            vendor_info = get_preferred_vendor(item_id)
            unit_cost = _safe_decimal(vendor_info.get('cost'))

        extended = qty * unit_cost

        line = PurchaseLine(
            purchase=purchase,
            item_fk=item,
            item={
                'item_id': item.pk,
                'ida_item': getattr(item, 'ida', ''),
                'description': item.name,
            },
            quantity={
                'active': float(qty),
                'staged': float(qty),
                'remaining': float(qty),
            },
            cost={
                'unit': float(unit_cost),
                'extended': float(extended),
            },
        )
        line.save()
        line_count += 1
        total_cost += extended

    # Recompute totals from lines via the single totals engine.
    # JSON is the source of truth; scalar `total` is synced by the engine.
    purchase.update_sell_cost_totals(persist=True)

    logger.info(
        "Created draft purchase #%s for vendor %s (%s lines, total=%s)",
        purchase.pk, vendor.company, line_count, total_cost,
    )

    return {
        'purchase_id': purchase.pk,
        'vendor_id': vendor_id,
        'vendor_name': vendor.company,
        'status': 'planned',
        'line_count': line_count,
        'total': float(total_cost),
    }
