# Item Model Reference


<!-- TOC START -->

## Table of Contents

- [Item Model Reference](#item-model-reference)
  - [Table of Contents](#table-of-contents)
  - [Field Summary (Selected)](#field-summary-selected)
  - [JSON Schemas](#json-schemas)
    - [price](#price)
    - [cost](#cost)
    - [catalog](#catalog)
    - [quantity (snapshot)](#quantity-snapshot)
  - [Validation Path](#validation-path)
  - [Deprecations / Pending Decisions](#deprecations-pending-decisions)
  - [Testing Invariants](#testing-invariants)
  - [Example Creation](#example-creation)
  - [Setup / Implementation Checklist](#setup-implementation-checklist)
  - [Future Enhancements](#future-enhancements)

<!-- TOC END -->

Purpose: Canonical description of the `Item` model structure, JSON schemas, invariants, and current cleanup decisions. Pairs with `cleanup-roadmap.md`.

## Field Summary (Selected)

| Field | Type | Notes |
|-------|------|-------|
| name | Char(160) | Required, indexed |
| sku | Char(80), unique nullable | Optional external code; may become case-insensitive constraint later |
| kind | Choice (physical/service/bundle) | Indexed for catalog filtering |
| uom / base_uom | Char | Unit of measure + canonical base for conversions |
| default_cost / default_price | (removed) | Scalars removed; JSON `price.base` & `cost.avg/standard` authoritative |
| gls | JSON | GL account refs: {inventory, cogs, revenue, variance} (extendable) |
| price | JSON | Structured pricing (schema below) |
| cost | JSON | Structured costing (schema below) |
| catalog | JSON | Category, attributes, web metadata, flags |
| quantity | JSON | Roll-up inventory status snapshot (on_hand, allocated, available, on_order) |
| security_level | Int | Access / internal gating |
| is_print_not | Bool | (Alias exposed as `is_print_suppressed`) legacy name retained one release |

## JSON Schemas

### price

```json
{
  "base": Decimal|null,
  "msrp": Decimal|null,
  "tiers": [ {"level": str, "price": Decimal}, ... ],
  "qty_breaks": [ {"min_qty": int, "unit_price": Decimal} | {"min_qty": int, "variant_item_id": int}, ... ],
  "currency": "USD",
  "history": [ {"dt_utc": iso8601, "field": str, "old": any, "new": any}, ... ]
}
```

Invariants:
 
- `qty_breaks` strictly ascending by `min_qty`, unique, each element has either `unit_price` or `variant_item_id`.
- `currency` 3 uppercase letters.

### cost

```json
{
  "standard": Decimal|null,
  "last": Decimal|null,
  "avg": Decimal|null,
  "landed": Decimal|null,
  "currency": "USD",
  "components": { "freight": Decimal?, "duty": Decimal?, ... },
  "breaks": [ {"min_qty": int, "unit_cost": Decimal} | {"min_qty": int, "variant_item_id": int}, ... ],
  "history": [ {"dt_utc": iso8601, "field": str, "old": any, "new": any}, ... ]
}
```

Invariants mirror pricing breaks; `breaks` sorted & unique by `min_qty`. `history` bounded to last 50 entries (change detection on standard/last/avg/landed fields).

### catalog


```json
{
  "categories": [str],
  "attributes": { key: value },
  "web": { "slug": str?, "title": str?, "short": str?, "seo": { ... } },
  "flags": { "featured": bool?, "seasonal": bool?, "restricted": bool? }
}
```

### quantity (snapshot)


```json
{
  "on_hand": Decimal?,
  "allocated": Decimal?,
  "available": Decimal?,
  "on_order": Decimal?
}
```

`available` should match `on_hand - allocated` if maintained internally; health checks will flag divergence.

## Validation Path

`Item.clean()` enforces:

- Currency presence & length=3 for price/cost; auto uppercases.
- Break list structure + ordering + uniqueness before save.

`Item.save()` still performs defensive schema merges; future direction is to push more logic into explicit validators + invariant tests.

## Deprecations / Pending Decisions

| Topic | Decision Status | Notes |
|-------|-----------------|-------|
| Scalar `default_price/default_cost` | Removed | Scalars dropped; migration required to clean schema |
| Boolean `is_print_not` name | Renaming | Use `is_print_suppressed` alias now; full rename later |
| Flag booleans cluster | Pending | Evaluate consolidation into `catalog.flags` or new JSON field |

## Testing Invariants

`tests/test_item_invariants.py` covers: currency format, break ordering, normalization & alias property.

## Example Creation

```python
from apps.products.models import Item
item = Item.objects.create(name="Widget X", sku="WX-001", price={"base": "19.99", "currency": "usd"})
item.full_clean()  # will uppercase currency
item.save()
```

## Setup / Implementation Checklist

- [ ] Apply migration removing `default_price` / `default_cost` columns from DB (if still present) and related references.
- [ ] Validate `price.history` / `cost.history` rotation (max 50) via tests.
- [ ] Decide on enforcement for `quantity.available == on_hand - allocated` (warning vs hard error).
- [ ] Confirm SKU case-insensitive uniqueness at DB level (add functional index if Postgres).
- [ ] Populate any `catalog.web.slug` missing values (management command optional).
- [ ] Review `tax_code.jurisdiction_params` usage; implement jurisdiction-specific resolver service if needed.
- [ ] Add atomic quantity adjustment helpers (prevent race conditions).
- [ ] Expose schema descriptor dicts (`PRICE_SCHEMA_DESC`, etc.) in API docs.

## Future Enhancements

- Add Postgres partial indexes (is_active, kind) & trigram search (name, sku) when switching primary dev DB.
- Cost and price histories now present (rotation implemented, expand with actor UUID/user if audit needed).
- Health command section for divergence in `quantity.available` vs computed.

---
Last updated: 2025-09-04
