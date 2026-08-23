# Pricing Architecture

> **Last updated**: 2026-08-09
> **Owner**: Alice
> **Backend**: `apps/products/services/pricing.py`
> **Models**: `Item.price` (JSON), `Catalog`, `CatalogLine`, `OrgItem`
> **WC2 heritage**: `Get_Price`, `DiscountApply`, `PriceBelowMargi`, `PriceMatrix`

---

## How Pricing Works

Every line on every transaction resolves its unit price through a single chain.
The chain tries the most specific source first and falls back to broader defaults.
The user is always in control — the system warns but never overrides.

**Ask Alice:** "What price will customer X get for item Y?" and she will
walk the chain and explain why.

---

## Resolution Chain

| Priority | Source | What it means |
|----------|--------|---------------|
| **0** | Catalog item-specific price | Item listed in an active catalog for this customer |
| **1** | OrgItem contract override | Customer-specific price in `OrgItem.config.price_override` |
| **2** | Customer price_level on item | Customer's level (retail/wholesale/etc.) → `Item.price.{level}` |
| **3** | Explicit price_level | Line or header override |
| **4** | Item base price | `Item.price.base` |
| **5** | Fallback | $0 — item has no price data |
| **+** | Quantity breaks | Applied after level resolution (see below) |
| **+** | Universal catalog % | Blanket discount on all products for matching customers |
| **⚠** | Margin warning | Flag if below floor — **user decides, system does not override** |

### Price Level Resolution

When multiple levels are available, priority is: **line > header > customer > default**.

```
resolve_price_level(
    line_level='sample',        # ← wins if set (user override)
    header_level='wholesale',   # ← inherited from customer at order creation
    customer_level='retail',    # ← org default
) → 'sample'
```

### Four Price Levels

| Level | Typical use |
|-------|-------------|
| `retail` | Walk-in / end consumer |
| `wholesale` | Resellers, volume buyers |
| `distributor` | Distribution partners |
| `sample` | Sample/demo pricing |

Plus `base` (list price) and `msrp` (manufacturer suggested). Stored as keys
in `Item.price` JSON:

```json
{
    "base": 15.00,
    "retail": 12.00,
    "wholesale": 10.00,
    "distributor": 8.50,
    "sample": 5.00,
    "msrp": 18.00
}
```

---

## Quantity Breaks

Each break row carries per-level columns — both dollar price and percentage:

```json
{
    "qty_breaks": [
        {"min_qty": 1,   "max_qty": 24,  "base": 15.00, "retail": 12.00, "wholesale": 10.00},
        {"min_qty": 25,  "max_qty": 99,  "base": 14.00, "retail": 11.00, "wholesale_pct": 33.3},
        {"min_qty": 100, "max_qty": null, "base": 12.50, "retail": 10.00, "wholesale": 8.00}
    ]
}
```

**Rules:**
- Dollar price wins when present
- Percentage calculates from the break's `base` (or `Item.price.base` if no break base)
- Alice recalculates percentage-based levels when base price changes
- Legacy `unit_price` key still works (backward compatible)
- Highest break where `quantity >= min_qty` applies

---

## Catalog Pricing

Catalogs override the standard price chain. Two modes:

### Item-Specific Catalog
A `CatalogLine` with a fixed price or tiers for a specific item.
Highest priority — skips the entire standard chain.

```
Catalog "Summer Sale" (priority=10, applies_to={contact_types: ['wholesale']})
  └── CatalogLine: Item #42, price_unit=$7.50
```

### Universal % Catalog
A blanket discount applied to ALL products for matching customers.
Applied **after** the standard chain resolves the base price.

```
Catalog "Preferred Wholesale" (is_universal_pct=True, universal_pct=15)
  → 15% off whatever the customer's price_level price is
```

### Catalog Targeting

Catalogs apply to customers via:
- `customer_orgbase` FK — specific customer
- `applies_to.contacts` — list of customer IDs
- `applies_to.contact_types` — price_level match (e.g., `['wholesale']`)
- `applies_to.all` — universal
- No scope + no FK — applies to everyone

Higher `priority` value wins when multiple catalogs match.
Active date range (`dt_effective_start` / `dt_effective_end`) enforced.

---

## Margin Warning

When the resolved price produces a margin below the configured floor
(Setting `pricing_config.minimum_margin_pct`, default 15%), the system
returns `below_margin_floor: true`.

**The system does not override the price.** The user is in control.
The UI should display a warning — yellow highlight, "Margin below 15%".
WC2 heritage: `PriceBelowMargi` warned but never blocked.

---

## Files

| File | What it does |
|------|-------------|
| `apps/products/services/pricing.py` | Full resolution chain, qty breaks, catalog lookup, margin check |
| `apps/products/models/catalog.py` | Catalog + CatalogLine models |
| `apps/products/models/item.py` | Item.price JSON (levels, qty_breaks) |
| `apps/products/models/org_item.py` | OrgItem.config.price_override (contract prices) |
| `apps/core/management/commands/seed_select_lists.py` | Price level select list |
| `tests/test_pricing.py` | Resolution chain tests |

---

## WC2 → WC3 Translation

| WC2 | WC3 |
|-----|-----|
| `Get_Price` | `resolve_price()` |
| `DiscountApply` | Built into `resolve_unit_price()` |
| `PriceBelowMargi` | `below_margin_floor` flag (warning only) |
| `PriceMatrix` / `ImportPriceMatrix` | `Item.price.qty_breaks` JSON |
| `SpecialDiscount` + `ItemDiscount` | `Catalog` + `CatalogLine` |
| `typeSale` (A/B/C/D/MSRP) | `price_level` (retail/wholesale/distributor/sample/base/msrp) |
| `OrdLnExtend` discount calc | `resolve_unit_price()` + `recalculate_line()` |

---

## Transaction Feature Gap List

Features identified during WC2 salvage (2026-08-09). Not blocking release —
build when asked or when Alice identifies demand.

| Feature | Status | Notes |
|---------|--------|-------|
| Returns | Done | Negative invoice (credit_note type). No separate RMA model — same chain, negative quantities. |
| Terms / early payment discount | Done | Wired in payment_pending.py — checks invoice date vs payment date, auto-applies discount within window |
| Customer AR statements | Gap | Outbound statement generation (list open invoices + payments) |
| Multi-currency on transactions | Thin | currency in cost envelope; no exchange rate field/lookup on header |
| Recurring orders / subscriptions | Gap | Auto-generate orders on schedule |
| Drop ship | Gap | Line flagged to ship from vendor to customer; auto-generate PO |
| Landed cost allocation | Thin | Fields exist on InventoryLayer; no allocation service |
| Batch operations | Gap | Batch invoice, batch payment, batch ship orchestration |
| Approval workflows | Gap | Price/credit/large order approvals |
| Consignment | Gap | Goods at customer location, billed when sold |
