"""Inventory bounds recommendation service.

Computes recommended inventory_min (reorder point) and inventory_max
for an Item based on:
  - Sales velocity (ItemUsage monthly actuals)
  - BOM consumption (as a component in assemblies)
  - Lead time (from preferred vendor OrgItem or ItemUsage metrics)
  - Pending records (on_so, on_po — committed intent signals)
  - Receipt history (InventoryLayer receipt patterns)
  - Margin factor (higher margin justifies more safety stock)

Best practices implemented:
  - Safety stock uses service-level z-score × demand std dev × √lead time
  - Margin-weighted: high-margin items get proportionally more buffer
  - Pending records amplify demand signal (on_so = known future consumption)
  - BOM consumption cascades parent demand to child components
  - Lead time variability factored into safety stock when data available
  - EOQ (Economic Order Quantity) for inventory_max when cost data available

The recommender writes to Item.quantity.inventory_min/max. OrgItem thresholds
(quantity_minimum/maximum) remain per-vendor inputs — not overwritten.
"""
from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.apps import apps as dj_apps
from django.db.models import Avg, Q, StdDev, Sum

logger = logging.getLogger(__name__)


def _get_models():
    """Lazy-load Django models."""
    Item = dj_apps.get_model('products', 'Item')
    OrgItem = dj_apps.get_model('products', 'OrgItem')
    ItemUsage = dj_apps.get_model('products', 'ItemUsage')
    BillOfMaterial = dj_apps.get_model('products', 'BillOfMaterial')
    InventoryLayer = dj_apps.get_model('products', 'InventoryLayer')
    return Item, OrgItem, ItemUsage, BillOfMaterial, InventoryLayer


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ── Adaptive window ──────────────────────────────────────────────────

# CV bands from supply chain best practice (SAP APO, Oracle WMS, SPC literature).
# Window must be >= 3 months (statistical significance) and <= 12 months (relevance).
CV_BANDS = [
    # (cv_threshold, months, label)
    (0.25, 12, 'very_stable'),    # CV < 0.25 — use all data
    (0.50,  9, 'stable'),         # 0.25 ≤ CV < 0.50 — moderate stability
    (0.75,  6, 'moderate'),       # 0.50 ≤ CV < 0.75 — classic window
    (1.00,  4, 'volatile'),       # 0.75 ≤ CV < 1.00 — focus on recent
    (None,  3, 'very_volatile'),  # CV ≥ 1.00 — almost instant-reactive
]


def _compute_adaptive_window(item_id: int) -> Dict[str, Any]:
    """Determine trailing window length based on demand volatility.

    Pulls 12 months of ItemUsage, computes coefficient of variation
    (CV = σ/μ), and maps to an appropriate window size.

    High volatility → short window (responsive to recent changes)
    Low volatility  → long window (more data = more confidence)

    Returns:
        {months, cv, band, monthly_qtys}
    """
    _, _, ItemUsage, _, _ = _get_models()

    usages = (
        ItemUsage.objects
        .filter(item_id=item_id, is_active=True)
        .order_by('-year', '-month')[:12]
    )

    monthly_qtys = []
    for u in usages:
        metrics = u.metrics if isinstance(u.metrics, dict) else {}
        sales_qty = _safe_float(metrics.get('sales.quantity.actual', 0))
        bom_qty = _safe_float(metrics.get('bill_of_material.quantity.actual', 0))
        monthly_qtys.append(sales_qty + bom_qty)

    if len(monthly_qtys) < 3:
        # Insufficient data — use default window, can't assess volatility
        return {'months': 6, 'cv': None, 'band': 'insufficient_data', 'monthly_qtys': monthly_qtys}

    avg = sum(monthly_qtys) / len(monthly_qtys)
    if avg <= 0:
        return {'months': 6, 'cv': 0, 'band': 'no_demand', 'monthly_qtys': monthly_qtys}

    variance = sum((x - avg) ** 2 for x in monthly_qtys) / (len(monthly_qtys) - 1)
    std_dev = math.sqrt(variance)
    cv = std_dev / avg

    # Map CV to window size
    months = 6
    band = 'moderate'
    for threshold, m, label in CV_BANDS:
        if threshold is None or cv < threshold:
            months = m
            band = label
            break

    return {'months': months, 'cv': round(cv, 4), 'band': band, 'monthly_qtys': monthly_qtys}


# ── Data collectors ──────────────────────────────────────────────────

def _get_sales_velocity(item_id: int, months: int = 6) -> Dict[str, float]:
    """Get average daily sales and std dev from ItemUsage trailing N months.

    Returns:
        {avg_daily, std_dev_daily, avg_monthly, months_with_data}
    """
    _, _, ItemUsage, _, _ = _get_models()

    usages = (
        ItemUsage.objects
        .filter(item_id=item_id, is_active=True)
        .order_by('-year', '-month')[:months]
    )

    monthly_qtys = []
    for u in usages:
        metrics = u.metrics if isinstance(u.metrics, dict) else {}
        sales_qty = _safe_float(metrics.get('sales.quantity.actual', 0))
        bom_qty = _safe_float(metrics.get('bill_of_material.quantity.actual', 0))
        monthly_qtys.append(sales_qty + bom_qty)

    if not monthly_qtys:
        return {'avg_daily': 0, 'std_dev_daily': 0, 'avg_monthly': 0, 'months_with_data': 0}

    avg_monthly = sum(monthly_qtys) / len(monthly_qtys)
    avg_daily = avg_monthly / 30.0

    if len(monthly_qtys) > 1:
        mean = avg_monthly
        variance = sum((x - mean) ** 2 for x in monthly_qtys) / (len(monthly_qtys) - 1)
        std_dev_monthly = math.sqrt(variance)
        std_dev_daily = std_dev_monthly / math.sqrt(30.0)
    else:
        std_dev_daily = avg_daily * 0.3  # assume 30% CV when insufficient data

    return {
        'avg_daily': avg_daily,
        'std_dev_daily': std_dev_daily,
        'avg_monthly': avg_monthly,
        'months_with_data': len(monthly_qtys),
    }


def _get_bom_demand(item_id: int, months: int = 6) -> float:
    """Get additional daily demand from BOM consumption as a component.

    When this item is a child in BOMs, the parent's sales velocity
    multiplied by the BOM quantity drives component demand.
    """
    _, _, ItemUsage, BillOfMaterial, _ = _get_models()

    bom_lines = (
        BillOfMaterial.objects
        .filter(child_item_id=item_id, is_active=True)
        .values('parent_item_id', 'quantity', 'scrap_factor', 'yield_pct')
    )

    total_daily_demand = 0.0
    for line in bom_lines:
        parent_velocity = _get_sales_velocity(line['parent_item_id'], months)
        qty_per = _safe_float(line['quantity'], 1.0)
        scrap = _safe_float(line['scrap_factor'], 0.0)
        yield_pct = _safe_float(line['yield_pct'], 100.0)

        # Effective qty needed = qty_per * (1 + scrap) / (yield / 100)
        effective_qty = qty_per * (1 + scrap)
        if yield_pct > 0:
            effective_qty = effective_qty / (yield_pct / 100.0)

        total_daily_demand += parent_velocity['avg_daily'] * effective_qty

    return total_daily_demand


def _get_lead_time(item_id: int) -> Dict[str, float]:
    """Get lead time in days from OrgItem vendor data or ItemUsage metrics.

    Returns:
        {lead_time_days, lead_time_std_dev}
    """
    _, OrgItem, ItemUsage, _, _ = _get_models()

    # Try OrgItem for vendor-type orgs
    org_items = (
        OrgItem.objects
        .filter(item_id=item_id, is_active=True)
        .values('data')
    )

    lead_times = []
    for oi in org_items:
        data = oi['data'] if isinstance(oi['data'], dict) else {}
        lt = _safe_float(data.get('lead_time_days'))
        if lt > 0:
            lead_times.append(lt)

    # Also check ItemUsage for lead.time metric
    recent_usage = (
        ItemUsage.objects
        .filter(item_id=item_id, is_active=True)
        .order_by('-year', '-month')[:6]
    )
    for u in recent_usage:
        metrics = u.metrics if isinstance(u.metrics, dict) else {}
        lt = _safe_float(metrics.get('lead.time'))
        if lt > 0:
            lead_times.append(lt)

    if not lead_times:
        return {'lead_time_days': 14.0, 'lead_time_std_dev': 3.0}  # conservative default

    avg_lt = sum(lead_times) / len(lead_times)
    if len(lead_times) > 1:
        variance = sum((x - avg_lt) ** 2 for x in lead_times) / (len(lead_times) - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = avg_lt * 0.2  # assume 20% variability

    return {'lead_time_days': avg_lt, 'lead_time_std_dev': std_dev}


def _get_pending_signals(item_id: int) -> Dict[str, float]:
    """Read pending commitments from Item.quantity JSONB.

    Pending records show committed intent:
      on_so = demand committed but not shipped
      on_po = supply committed but not received
      on_wo = work order demand (BOM consumption in progress)
      on_p  = proposal demand (probability-weighted)
    """
    Item, _, _, _, _ = _get_models()

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'on_so': 0, 'on_po': 0, 'on_wo': 0, 'on_p': 0, 'net_committed': 0}

    qty = item.quantity if isinstance(item.quantity, dict) else {}
    on_so = _safe_float(qty.get('on_so'))
    on_po = _safe_float(qty.get('on_po'))
    on_wo = _safe_float(qty.get('on_wo'))
    on_p = _safe_float(qty.get('on_p'))

    # Net committed demand beyond normal velocity
    net_committed = (on_so + on_wo + on_p * 0.5) - on_po

    return {
        'on_so': on_so,
        'on_po': on_po,
        'on_wo': on_wo,
        'on_p': on_p,
        'net_committed': max(0, net_committed),  # only positive = unfilled demand
    }


def _get_margin_factor(item_id: int) -> float:
    """Get margin-based weighting factor.

    Higher margin items justify more safety stock — the opportunity cost
    of a stockout is proportional to the margin lost.

    Returns factor >= 1.0 (1.0 = no margin boost, 1.5 = 50% boost)
    """
    Item, _, _, _, _ = _get_models()

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return 1.0

    margin_pct = _safe_float(getattr(item, 'margin_pct', 0))
    if margin_pct <= 0:
        # Try to compute from price/cost
        price = item.price if isinstance(item.price, dict) else {}
        cost = item.cost if isinstance(item.cost, dict) else {}
        base_price = _safe_float(price.get('base'))
        std_cost = _safe_float(cost.get('standard') or cost.get('avg') or cost.get('last'))
        if base_price > 0 and std_cost > 0:
            margin_pct = ((base_price - std_cost) / base_price) * 100

    # Scale: 0% margin → 1.0x, 25% → 1.125x, 50% → 1.25x, 75% → 1.375x
    # Capped at 1.5x to avoid over-stocking even high-margin items
    factor = 1.0 + min(margin_pct / 200.0, 0.5)
    return factor


def _get_receipt_pattern(item_id: int) -> Dict[str, float]:
    """Analyze receipt patterns from InventoryLayer for typical order size.

    Returns:
        {avg_receipt_qty, receipt_count}
    """
    _, _, _, _, InventoryLayer = _get_models()

    layers = (
        InventoryLayer.objects
        .filter(item_id=item_id, is_active=True)
        .order_by('-dt_created')[:20]
    )

    receipt_qtys = []
    for layer in layers:
        qty = layer.quantity if isinstance(layer.quantity, dict) else {}
        received = _safe_float(qty.get('received') or qty.get('original'))
        if received > 0:
            receipt_qtys.append(received)

    if not receipt_qtys:
        return {'avg_receipt_qty': 0, 'receipt_count': 0}

    return {
        'avg_receipt_qty': sum(receipt_qtys) / len(receipt_qtys),
        'receipt_count': len(receipt_qtys),
    }


# ── Main recommender ─────────────────────────────────────────────────

def recommend_inventory_bounds(
    item_id: int,
    *,
    z_score: float = 1.65,
    trailing_months: Optional[int] = None,
    apply: bool = False,
) -> Dict[str, Any]:
    """Recommend inventory_min and inventory_max for an item.

    The trailing window (n) adapts to the item's demand volatility:
      CV < 0.25  → 12 months (very stable — use all data)
      CV 0.25-0.5 → 9 months (stable)
      CV 0.5-0.75 → 6 months (moderate — classic window)
      CV 0.75-1.0 → 4 months (volatile — focus on recent)
      CV ≥ 1.0   → 3 months (very volatile — instant-reactive)

    Pass trailing_months to override the adaptive window.

    Formula:
        avg_daily_demand = sales_velocity + bom_component_demand
        safety_stock = z_score × √(lt × σd² + d² × σlt²) × margin_factor
        pending_buffer = max(0, net_committed_demand - on_po)

        inventory_min = (lead_time × avg_daily_demand) + safety_stock + pending_buffer
        inventory_max = inventory_min + economic_order_quantity

    Args:
        item_id: Item primary key
        z_score: Service level confidence (1.28=90%, 1.65=95%, 2.33=99%)
        trailing_months: Override adaptive window (None = auto from volatility)
        apply: If True, write results to Item.quantity.inventory_min/max

    Returns:
        Dict with recommendation, inputs, and reasoning.
    """
    Item, _, _, _, _ = _get_models()

    # Determine adaptive window
    adaptive = _compute_adaptive_window(item_id)
    effective_months = trailing_months if trailing_months is not None else adaptive['months']

    # Collect all inputs using the adaptive window
    velocity = _get_sales_velocity(item_id, effective_months)
    bom_demand = _get_bom_demand(item_id, effective_months)
    lead_time = _get_lead_time(item_id)
    pending = _get_pending_signals(item_id)
    margin_factor = _get_margin_factor(item_id)
    receipts = _get_receipt_pattern(item_id)

    # Total daily demand
    avg_daily_demand = velocity['avg_daily'] + bom_demand
    demand_std_dev = velocity['std_dev_daily']

    # Lead time
    lt_days = lead_time['lead_time_days']
    lt_std_dev = lead_time['lead_time_std_dev']

    # Safety stock: accounts for both demand variability and lead time variability
    # Full formula: SS = z × √(lt × σd² + d² × σlt²)
    if avg_daily_demand > 0 or demand_std_dev > 0:
        demand_variance = lt_days * (demand_std_dev ** 2)
        lt_variance = (avg_daily_demand ** 2) * (lt_std_dev ** 2)
        safety_stock = z_score * math.sqrt(demand_variance + lt_variance)
    else:
        safety_stock = 0

    # Apply margin factor
    safety_stock *= margin_factor

    # Lead time demand
    lead_time_demand = lt_days * avg_daily_demand

    # Pending buffer — committed demand not yet covered by inbound
    pending_buffer = pending['net_committed']

    # inventory_min = reorder point
    inventory_min = lead_time_demand + safety_stock + pending_buffer

    # Economic order quantity for inventory_max
    if receipts['avg_receipt_qty'] > 0:
        eoq = receipts['avg_receipt_qty']
    elif avg_daily_demand > 0:
        eoq = lead_time_demand * 2  # 2× lead time demand as default batch
    else:
        eoq = 0

    # inventory_max = min + order quantity
    inventory_max = inventory_min + eoq

    # Round to reasonable precision
    inventory_min = round(max(0, inventory_min), 2)
    inventory_max = round(max(inventory_min, inventory_max), 2)

    result = {
        'item_id': item_id,
        'inventory_min': inventory_min,
        'inventory_max': inventory_max,
        'adaptive_window': {
            'effective_months': effective_months,
            'cv': adaptive['cv'],
            'band': adaptive['band'],
            'override': trailing_months is not None,
        },
        'inputs': {
            'velocity': velocity,
            'bom_component_demand_daily': bom_demand,
            'total_daily_demand': avg_daily_demand,
            'lead_time': lead_time,
            'pending': pending,
            'margin_factor': margin_factor,
            'receipts': receipts,
        },
        'calculation': {
            'z_score': z_score,
            'safety_stock': round(safety_stock, 2),
            'lead_time_demand': round(lead_time_demand, 2),
            'pending_buffer': round(pending_buffer, 2),
            'eoq': round(eoq, 2),
        },
        'applied': False,
    }

    if apply:
        try:
            item = Item.objects.get(pk=item_id)
            if not isinstance(item.quantity, dict):
                item.quantity = {}
            item.quantity['inventory_min'] = inventory_min
            item.quantity['inventory_max'] = inventory_max
            item.save(update_fields=['quantity', 'dt_modified', 'version'])
            result['applied'] = True
            logger.info(
                "Applied inventory bounds for item %s: min=%.2f, max=%.2f",
                item_id, inventory_min, inventory_max,
            )
        except Item.DoesNotExist:
            logger.warning("Item %s not found — bounds not applied", item_id)

    return result


def recommend_bounds_bulk(
    item_ids: Optional[List[int]] = None,
    *,
    z_score: float = 1.65,
    trailing_months: Optional[int] = None,
    apply: bool = False,
    kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Recommend inventory bounds for multiple items.

    If item_ids is None, processes all active physical items.
    Use kind='physical' to restrict to physical goods only.
    trailing_months=None uses adaptive window per item (recommended).

    Returns list of recommendation dicts.
    """
    Item, _, _, _, _ = _get_models()

    if item_ids is None:
        qs = Item.objects.filter(is_active=True)
        if kind:
            qs = qs.filter(kind=kind)
        item_ids = list(qs.values_list('pk', flat=True))

    results = []
    for item_id in item_ids:
        try:
            rec = recommend_inventory_bounds(
                item_id,
                z_score=z_score,
                trailing_months=trailing_months,
                apply=apply,
            )
            results.append(rec)
        except Exception as e:
            logger.error("Failed to recommend bounds for item %s: %s", item_id, e)
            results.append({'item_id': item_id, 'error': str(e)})

    return results
