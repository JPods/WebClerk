# Pricing & Catalogs — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 SpecialDiscount/PriceMatrix mining (27 files)

---

## Overview

One function resolves any price: `resolve_price(item, contact, qty, date)`. Returns the price, which cascade step determined it, margin %, and whether it's below floor. Below-margin prices never block shipment — flag and ship, review in dashboard.

---

## The Cascade (first match wins, no stacking)

```
1. price_locked          → manual override on the line — skip everything
2. OrgItem               → negotiated price for this vendor+item
3. Catalog rule          → highest-priority matching catalog:
   a. Universal %        → blanket % off all items
   b. CatalogLine match  → by specific item, category, or vendor scope
   c. Qty break          → min_qty/max_qty range on CatalogLine
4. Contact price level   → wholesale/distributor/retail tier
5. Item base price       → fallback
```

One path wins. The `resolved_by` field on PriceResolution tells you which step.

---

## PriceResolution (what resolve_price returns)

```python
PriceResolution(
    price=Decimal('59.49'),          # final unit price
    base_price=Decimal('69.99'),     # item's base before adjustments
    discount_pct=Decimal('15.0'),    # total discount applied
    discount_amount=Decimal('10.50'),
    resolved_by='catalog_line',      # which cascade step
    catalog_id=5,                    # which catalog matched
    catalog_name='Summer Sale 2026',
    margin_pct=Decimal('51.53'),     # (price - cost) / cost × 100
    below_margin_floor=False,
    price_locked=False,
)
```

---

## Catalog Model

```
Catalog (the promotion/agreement)
  ├── name                          "Summer Sale 2026"
  ├── dt_effective_start / end      auto-expires, no cleanup needed
  ├── priority                      higher wins when multiple match
  ├── applies_to                    JSON: {contacts: [id], contact_types: ['wholesale'], all: false}
  ├── is_universal_pct              true = blanket % on all items
  ├── universal_pct                 the blanket % (when universal)
  ├── margin_floor                  minimum margin % — below creates Action alert
  ├── orgbase FK                    vendor/manufacturer who publishes
  ├── customer_orgbase FK           target customer org (optional)
  ├── connection FK                 sync connection for Ingrid integration
  │
  └── CatalogLine[] (the rules)
       ├── item FK                  specific item (or null for scope-based)
       ├── scope                    JSON: {items: [id], categories: [], vendors: [], all_items: false}
       ├── adjustment_type          percent_off | fixed_price | amount_off | price_level
       ├── adjustment_value         15.0 (meaning depends on type)
       ├── min_qty / max_qty        qty break range (null = any)
       ├── price_unit               fixed price override
       ├── discount_percent         % off
       └── discount_amount          $ off
```

---

## PO Line Default Cost (purchasing side)

When creating a PO line, the default cost cascades:

```
1. OrgItem (this vendor's price for this item)
2. Setting rule (last, avg, lowest_vendor, landed)
```

The buying flow: Item → ItemXRef (vendor's part#) → OrgItem (vendor's price) → PO line.

JSON viewer on PO lines shows ALL vendors for the item — not just this PO's vendor — plus the cost layer stack.

---

## Ingrid Integration (future — Stage 5)

Manufacturer creates a Catalog → Ingrid pushes to resellers via Connection/Bundle sync → reseller's price_resolver picks it up automatically → catalog expires when period ends.

The Catalog model already has the connection FK. Needs Connection execution layer to activate.

---

## Margin Floor

When `price_resolver` returns a price below the catalog's `margin_floor`:
- Creates an informational Action (priority=low)
- **Does NOT block shipment** — flag and ship, review in Commerce Dashboard
- The Action says: "BB005 priced at $3.50 produces 12% margin, below floor of 20%"

---

## Key Differences from WC2

| WC2 | WC3 |
|---|---|
| SpecialDiscount + ItemDiscount + PriceMatrix (3 separate mechanisms) | One Catalog model with CatalogLine rules |
| TypeSale string matching for customer→catalog | Explicit applies_to JSON + customer_orgbase FK |
| Five price columns (A/B/C/D/MSRP) on Item | price.tiers[] array with named levels |
| Console warning for below-margin | Action alert (informational, never blocks) |
| 36 pricing methods scattered | One `resolve_price()` function |

---

## Files

| File | Purpose |
|------|---------|
| `apps/products/services/price_resolver.py` | resolve_price() + cascade logic |
| `apps/products/models/catalog.py` | Catalog + CatalogLine models |
| `apps/products/models/org_item.py` | OrgItem (vendor×item price) |
| `apps/products/models/item_xref.py` | ItemXRef (vendor part number mapping) |
