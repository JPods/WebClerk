# Freight Estimation — Estimate, Reconcile, Adjust

**Established:** 2026-08-01
**Pattern from:** WC2 (Bill James)
**Improvement:** Weight-bracket segmentation + Alice nightly reconciliation

---

## The Pattern

1. **Estimate at order time** — weight of goods × carrier rate × freight factor
2. **Reconcile monthly** — compare estimated freight to actual carrier invoices
3. **Adjust the factor** — Alice proposes, admin accepts

This is the same feedback loop as WC2. The WC3 improvement is segmenting the
freight factor by carrier × weight bracket so it converges faster.

---

## How It Works

### At Order Time

When a line is added or quantity changes:

```
estimated_freight = total_weight × carrier_rate_per_lb × freight_factor
```

- `total_weight` — sum of `line.physical.weight × line.quantity.active` across all lines
- `carrier_rate_per_lb` — from the shipper's service (e.g., UPS Ground = $0.45/lb base)
- `freight_factor` — the fudge factor for this carrier + weight bracket

The estimate is stored in `totals.shipping` on the order.

### Weight Brackets

A single fudge factor averages a 5 lb package with a 500 lb pallet. They have
completely different error profiles. Segment by weight bracket:

| Bracket | Typical Variance | Why |
|---------|-----------------|-----|
| 0–5 lbs | Low ($1-3) | Standard package rates, predictable |
| 5–25 lbs | Low-Medium ($2-8) | Dimensional weight kicks in |
| 25–100 lbs | Medium ($5-20) | Oversize surcharges possible |
| 100–500 lbs | High ($20-80) | Pallet pricing, accessorial charges |
| 500+ lbs | High ($50-200) | Freight class, liftgate, residential surcharges |

### Freight Factors in Shipper Setting

Each shipper in Setting #481 carries freight factors per bracket:

```json
{
  "ida": "ups",
  "name": "UPS",
  "account": "1Z999AA10123456784",
  "connection_id": 42,
  "services": [...],
  "freight_factors": {
    "0-5":     1.12,
    "5-25":    1.08,
    "25-100":  1.15,
    "100-500": 1.22,
    "500+":    1.30
  },
  "rate_per_lb": {
    "UPS Ground":   0.45,
    "UPS 2nd Day":  1.20,
    "UPS Next Day": 2.50,
    "UPS 3 Day":    0.85
  }
}
```

Factor = 1.0 means perfect estimation. Factor > 1.0 means we historically
underestimate (actual costs are higher). Factor < 1.0 means we overestimate.

Initial factors start at 1.15 (15% cushion). Alice adjusts from there.

---

## Reconciliation

### What Alice Does Nightly

1. **Match** — find orders where actual carrier invoices exist (via carrier
   invoice import or manual entry in `metadata.shipping[]`)
2. **Compare** — estimated freight vs actual freight for each order
3. **Bucket** — group by carrier × weight bracket
4. **Calculate** — new factor = avg(actual / estimated) per bucket
5. **Propose** — write adjustment to data polishing dashboard
6. **Flag** — any order where variance > 15% gets flagged for review

### Monthly Admin Review

Alice presents a dashboard row per carrier × bracket:

| Carrier | Bracket | Orders | Avg Est | Avg Actual | Current Factor | Proposed Factor |
|---------|---------|--------|---------|------------|---------------|-----------------|
| UPS | 5-25 | 47 | $12.30 | $13.10 | 1.08 | 1.065 |
| FedEx | 25-100 | 12 | $34.50 | $41.20 | 1.15 | 1.19 |

Admin accepts or overrides. Accepted factors apply to future estimates immediately.

---

## Service

### `freight_estimation.py`

```python
def estimate_freight(lines, ship_via, shipper_setting):
    """Calculate estimated freight for an order.
    
    Args:
        lines: order lines with physical.weight
        ship_via: service value (e.g., 'UPS Ground')
        shipper_setting: config from Setting #481
    
    Returns:
        float: estimated freight amount
    """
    total_weight = sum(
        (line.get('physical', {}).get('weight', 0) or 0) 
        * (line.get('quantity', {}).get('active', 0) or 0)
        for line in lines
    )
    
    # Find the shipper and service
    shipper = find_shipper_for_service(ship_via, shipper_setting)
    if not shipper:
        return 0.0
    
    rate = shipper.get('rate_per_lb', {}).get(ship_via, 0.50)
    factor = get_freight_factor(total_weight, shipper)
    
    return round(total_weight * rate * factor, 2)


def get_freight_factor(weight, shipper):
    """Get the freight factor for this weight bracket."""
    factors = shipper.get('freight_factors', {})
    if weight <= 5:     return factors.get('0-5', 1.15)
    if weight <= 25:    return factors.get('5-25', 1.15)
    if weight <= 100:   return factors.get('25-100', 1.15)
    if weight <= 500:   return factors.get('100-500', 1.15)
    return factors.get('500+', 1.15)


def find_shipper_for_service(ship_via, setting):
    """Find which shipper owns this service value."""
    for shipper in setting.get('shippers', []):
        for svc in shipper.get('services', []):
            if svc.get('value') == ship_via:
                return shipper
    return None


def reconcile_freight(orders_with_actuals, shipper_setting):
    """Compare estimated vs actual freight, return proposed factor adjustments.
    
    Args:
        orders_with_actuals: list of {order_id, ship_via, estimated, actual, weight}
        shipper_setting: current config
    
    Returns:
        list of {carrier, bracket, current_factor, proposed_factor, sample_size, avg_variance}
    """
    from collections import defaultdict
    
    buckets = defaultdict(list)
    for o in orders_with_actuals:
        shipper = find_shipper_for_service(o['ship_via'], shipper_setting)
        if not shipper or not o['estimated']:
            continue
        bracket = weight_bracket(o['weight'])
        buckets[(shipper['ida'], bracket)].append(o['actual'] / o['estimated'])
    
    adjustments = []
    for (carrier, bracket), ratios in buckets.items():
        if len(ratios) < 5:  # need minimum sample size
            continue
        avg_ratio = sum(ratios) / len(ratios)
        shipper = next(s for s in shipper_setting['shippers'] if s['ida'] == carrier)
        current = shipper.get('freight_factors', {}).get(bracket, 1.15)
        proposed = round(current * avg_ratio, 3)
        adjustments.append({
            'carrier': carrier,
            'bracket': bracket,
            'current_factor': current,
            'proposed_factor': proposed,
            'sample_size': len(ratios),
            'avg_variance': round((avg_ratio - 1.0) * 100, 1),
        })
    
    return adjustments


def weight_bracket(weight):
    if weight <= 5:   return '0-5'
    if weight <= 25:  return '5-25'
    if weight <= 100: return '25-100'
    if weight <= 500: return '100-500'
    return '500+'
```

---

## Integration Points

| When | What happens |
|------|-------------|
| Line added/changed | `estimate_freight()` updates `totals.shipping` |
| Ship via changed | Re-estimate with new carrier's rates + factors |
| Carrier invoice imported | Stored in `metadata.shipping[].actual_cost` |
| Alice nightly | `reconcile_freight()` → data polishing dashboard |
| Admin accepts adjustment | Factor updated in shipper Setting #481 |

---

## Related

- Setting #481 — shipper configuration with accounts, services, freight factors
- `readmes/topics/ai/alice-data-polishing.md` — the reconciliation dashboard pattern
- `readmes/topics/transactions/order-detail.md` — order footer shows estimated shipping
