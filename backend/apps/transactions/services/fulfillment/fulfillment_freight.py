"""
freight_estimation.py — Estimate freight at order time, reconcile monthly.

Pattern: estimate = weight × rate × freight_factor
Freight factors segmented by carrier × weight bracket (0-5, 5-25, 25-100, 100-500, 500+).
Alice reconciles nightly: compares estimated vs actual carrier invoices, proposes factor adjustments.

Setting #481 (shippers) carries the factors per carrier.

Established: 2026-08-01. Pattern from WC2 (Bill James).
"""
from collections import defaultdict
from typing import Any


DEFAULT_FACTOR = 1.15  # 15% cushion until Alice calibrates
DEFAULT_RATE = 0.50    # $/lb fallback


def weight_bracket(weight: float) -> str:
    """Classify weight into a bracket for factor lookup."""
    if weight <= 5:   return '0-5'
    if weight <= 25:  return '5-25'
    if weight <= 100: return '25-100'
    if weight <= 500: return '100-500'
    return '500+'


def find_shipper_for_service(ship_via: str, setting: dict) -> dict | None:
    """Find which shipper owns this service value."""
    for shipper in setting.get('shippers', []):
        for svc in shipper.get('services', []):
            if svc.get('value') == ship_via:
                return shipper
    return None


def get_freight_factor(weight: float, shipper: dict) -> float:
    """Get the freight factor for this weight bracket."""
    factors = shipper.get('freight_factors', {})
    bracket = weight_bracket(weight)
    return factors.get(bracket, DEFAULT_FACTOR)


def estimate_freight(lines: list[dict], ship_via: str, shipper_setting: dict) -> float:
    """Calculate estimated freight for an order.

    Args:
        lines: order lines, each with physical.weight and quantity.active
        ship_via: service value (e.g., 'UPS Ground')
        shipper_setting: config from Setting #481

    Returns:
        Estimated freight amount (float, rounded to 2 decimal places)
    """
    total_weight = sum(
        (line.get('physical', {}).get('weight', 0) or 0)
        * (line.get('quantity', {}).get('active', 0) or 0)
        for line in lines
    )

    if total_weight <= 0 or not ship_via:
        return 0.0

    shipper = find_shipper_for_service(ship_via, shipper_setting)
    if not shipper:
        return round(total_weight * DEFAULT_RATE * DEFAULT_FACTOR, 2)

    rate = shipper.get('rate_per_lb', {}).get(ship_via, DEFAULT_RATE)
    factor = get_freight_factor(total_weight, shipper)

    return round(total_weight * rate * factor, 2)


def reconcile_freight(orders_with_actuals: list[dict], shipper_setting: dict) -> list[dict]:
    """Compare estimated vs actual freight, return proposed factor adjustments.

    Args:
        orders_with_actuals: list of dicts with keys:
            order_id, ship_via, estimated, actual, weight
        shipper_setting: current config from Setting #481

    Returns:
        List of adjustment proposals:
            carrier, bracket, current_factor, proposed_factor, sample_size, avg_variance_pct
    """
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    for o in orders_with_actuals:
        estimated = o.get('estimated', 0)
        actual = o.get('actual', 0)
        if not estimated or not actual:
            continue

        shipper = find_shipper_for_service(o.get('ship_via', ''), shipper_setting)
        if not shipper:
            continue

        bracket = weight_bracket(o.get('weight', 0))
        buckets[(shipper['ida'], bracket)].append(actual / estimated)

    adjustments = []
    for (carrier_ida, bracket), ratios in buckets.items():
        if len(ratios) < 5:  # minimum sample size
            continue

        avg_ratio = sum(ratios) / len(ratios)

        # Find current factor
        shipper = next(
            (s for s in shipper_setting.get('shippers', []) if s['ida'] == carrier_ida),
            None,
        )
        if not shipper:
            continue

        current = shipper.get('freight_factors', {}).get(bracket, DEFAULT_FACTOR)
        # New factor = current adjusted by the observed ratio
        proposed = round(current * avg_ratio, 3)

        adjustments.append({
            'carrier': carrier_ida,
            'bracket': bracket,
            'current_factor': current,
            'proposed_factor': proposed,
            'sample_size': len(ratios),
            'avg_variance_pct': round((avg_ratio - 1.0) * 100, 1),
        })

    return adjustments
