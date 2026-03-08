# Transaction Calculations & Inventory Transfer — Status & Plan

> **Version**: 2.0  
> **Updated**: 2026-02-16  
> **Scope**: Actual state of calculations today, known bugs, plan for fixes  
> **Companion**: `08-transaction-calculations.md` (design reference), `celery-redis-pending.md` (inventory processing)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Case Study: Order ID = 4](#case-study-order-id--4)
3. [Root Causes](#root-causes)
4. [Calculation Architecture (Actual)](#calculation-architecture-actual)
5. [Inventory Transfer Between Transactions](#inventory-transfer-between-transactions)
6. [File Map](#file-map)
7. [Fix Plan](#fix-plan)
8. [Data Migration](#data-migration)

---

## Executive Summary

Transaction calculations are **structurally complete**. Two of three known bugs are resolved; one critical issue remains:

| Bug | Impact | Severity | Status |
|-----|--------|----------|--------|
| **Quantity key mismatch** | R25 sends `quantity.ordered`; backend reads `quantity.staged` → extended = 0 | Critical | **FIXED** — R25 now sends `staged` on all transaction detail pages |
| **Header totals signal gap** | Only `ProposalLine` auto-recalculates parent totals; Order/Invoice/Purchase/WorkOrder do not | Critical | Open |
| **Line identity fragility** | `line.id ?? idx` broke editing for unsaved/transferred lines | High | **FIXED** — `line_number` scalar field + `lineKey()` helper |

The quantity-key and line-identity bugs were **data-shape issues**, not logic errors — the calculation formulas are correct, they just received zero input. The remaining **header totals signal gap** is the sole open critical bug.

### Line Number System (2026-02)

A `line_number` `IntegerField` (auto-assigned in increments of 10) was added to `BaseLineCore`, with a companion `line_increment` counter on `TransactionBaseModel`. This replaces the fragile `line.id ?? idx` pattern that failed for unsaved lines. R25 now uses `lineKey(line, idx)` → `line.line_number ?? line.id ?? idx` for all state handlers. See `lineHelpers.ts` in R25 and migration `0003_add_line_number_and_line_increment.py`.

---

## Case Study: Order ID = 4

### What the user sees

Order 4 has **1 line** with item 243: quantity 7, unit price $721.00.  
Expected: extended = $5,047.00, order total = $5,047.00.  
Actual: extended = $0.00, order total = $0.00.

### Raw data (from database)

```
Order 4:
  status: planned
  customer_id: 83
  totals: {subtotal: 0, discount: 0, tax: 0, total: 0, cost: 0, margin: 0, ...}

Line 3 (on Order 4):
  quantity: {"ordered": 7}              ← KEY IS "ordered", NOT "staged"
  price:    {"unit": 721.0, "extended": 0.0, "discount_amount": 0.0, ...}
  cost:     {"unit": 345.6, "extended": 0.0, ...}
```

### Why extended = 0

`_calculate_extended_price()` in `base_line_model.py` line 340:

```python
quantity = self.quantity.get("staged", 0) if self.quantity else 0
#                            ^^^^^^^^
# quantity dict is {"ordered": 7} — has no "staged" key
# → quantity = 0
# → extended = 0 × 721.0 = 0.0
```

### Why header totals = 0

Even if extended were correct, header totals would still be 0 because:

1. `order.update_sell_cost_totals()` sums `line.price.extended` across lines — which is 0.
2. The `register_line_totals_signals()` call that auto-triggers header recalculation on line save is **only registered for ProposalLine** (signals.py line 220). OrderLine saves don't trigger any header recalc.

### Full audit results

```
OrderLine     (3 total):  ALL use "ordered" key, 3/3 have extended=0
InvoiceLine   (1 total):  ALL use "ordered" key, 1/1 has extended=0
ProposalLine  (1 total):  ALL use "ordered" key, 1/1 has extended=0
PurchaseLine  (1 total):  ALL use "ordered" key, 0 broken (no sell price)
WorkOrderLine (0 total):  n/a
```

**Every sell-side line in the database has extended = 0.**

---

## Root Causes

### 1. Quantity Key Mismatch: `"ordered"` vs `"staged"`

**Frontend (React2025)** sends `"ordered"` everywhere:
- `LinesCard.tsx` → `quantity: { ordered: quantity }`
- `OrderDetail.tsx` → `quantity: { ...l.quantity, ordered: Number(value) }`
- `InvoiceDetail.tsx`, `ProposalDetail.tsx`, `PurchaseDetail.tsx`, `WorkorderDetail.tsx` — all use `ordered`

**Backend (webClerk3)** expects `"staged"`:
- `default_quantity()` returns `{"staged": 0, "actioned": 0, "remaining": 0, ...}`
- `_calculate_extended_price()` reads `self.quantity.get("staged", 0)` → gets 0
- `LineItemService._recalculate_line()` reads `staged`
- `LineItemService.update_quantity()` reads `staged`

**No normalization layer exists.** `save_view.py` does `setattr(line_obj, 'quantity', payload_value)` — a blind passthrough. Then `ensure_json_defaults()` skips normalization because `{"ordered": 7}` is truthy:

```python
# base_line_model.py line 314
if not self.quantity:          # {"ordered": 7} is truthy → skipped
    self.quantity = default_quantity(...)
```

**Some services already handle both keys defensively:**
- `transfer_utils.py` → checks `staged`, then `ordered`, then `remaining`
- `validation.py` → `qty.get('remaining', qty.get('ordered', 0))`
- But `_calculate_extended_price()` — the critical path — has no fallback

### 2. Header Totals Signal Gap

In `signals.py` line 220:

```python
# ProposalLine also triggers parent totals recalculation
register_line_totals_signals(ProposalLine, 'parent')
```

Only ProposalLine has the signal. OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine do **not** auto-recalculate their parent's `sell`, `cost`, or `totals` on save.

**Why it was only ProposalLine:** Likely historical — proposals were implemented first and the signal was added. When Order/Invoice/Purchase/WorkOrder were added, the signal registration was never extended.

---

## Calculation Architecture (Actual)

### Three Layers of Line Calculation

| Layer | File | Function | When Called |
|-------|------|----------|-------------|
| **Model save hook** | `base_line_model.py:340` | `_calculate_extended_price()` | Every `line.save()` |
| **Service layer** | `line_item_service.py:830` | `_recalculate_line()` | `update_line()`, `update_quantity()`, etc. |
| **Transaction save verify** | `transaction_save.py:93` | `calculate_line_extended()` | `save_transaction_with_lines()` |

All three use the same formula:
```
extended = (quantity × unit_price) - discount_amount
```

All three read `quantity.staged` → all three get 0 for current data.

### Save Flow

```
R25 Frontend → POST /wcapi/save/
                    │
                    ├── For each line payload:
                    │     setattr(line, 'quantity', {"ordered": 7})
                    │     setattr(line, 'price', {"unit": 721.0, ...})
                    │     line.save()
                    │       └── ensure_json_defaults()
                    │             ├── normalize_price_map()    ← strips unknown keys, keeps standard ones
                    │             ├── normalize_cost_map()     ← same
                    │             ├── (quantity not normalized) ← BUG: no normalize_quantity_map()
                    │             └── _calculate_extended_price()
                    │                   └── qty = self.quantity.get("staged", 0)  ← 0 (BUG)
                    │                   └── extended = 0 × 721.0 = 0.0
                    │
                    └── Django post_save signals:
                          ├── update_inventory_on_save() → Pending records (works)
                          ├── maintain_header_links()    → parent.refs.links (works)
                          └── update_totals_on_save()    → ONLY for ProposalLine (BUG)
```

### Header Totals

```python
# order_totals.py → compute_order_sell_cost_totals()
for ln in order.lines.all():
    sell_goods += ln.price.extended      # 0.0 because of qty key bug
    cost_goods += ln.cost.extended       # 0.0 because of qty key bug

# Result: sell.total = 0, cost.total = 0, totals.total = 0
```

Even when called manually (`order.update_sell_cost_totals()`), it produces zeros because the line extended prices are zero.

---

## Inventory Transfer Between Transactions

### Transaction Lifecycle

```
┌──────────┐     convert      ┌──────────┐     convert      ┌──────────┐
│ Proposal │ ──────────────→  │  Order   │ ──────────────→  │ Invoice  │
│ (quote)  │                  │  (sell)  │                  │  (bill)  │
└──────────┘                  └──────────┘                  └──────────┘
     ↓                              ↓                            ↓
  on_p ±                        on_so ±                      on_in ±
  (Pending)                     (Pending)                    (Pending)

┌──────────────┐                                        ┌──────────────┐
│   Purchase   │ ←─── created from any sell doc ──────  │  Work Order  │
│   (buy)      │                                        │  (make)      │
└──────────────┘                                        └──────────────┘
     ↓                                                       ↓
  on_po ±                                                on_wo ±
  (Pending)                                              (Pending)
```

### Transfer Services

| Conversion | Service File | Function |
|------------|-------------|----------|
| Proposal → Order | `proposal_to_order.py` | `transfer_proposal_to_order()` |
| Proposal → Purchase | `proposal_to_purchase.py` | `transfer_proposal_to_purchase()` |
| Order → Purchase | `order_to_purchase.py` | `transfer_order_to_purchase()` |
| Invoice → Purchase | `invoice_to_purchase.py` | `transfer_invoice_to_purchase()` |
| Purchase → Invoice | `purchase_to_invoice.py` | `transfer_purchase_to_invoice()` |
| Purchase → Order | `purchase_to_order.py` | `transfer_purchase_to_order()` |
| Purchase → Proposal | `purchase_to_proposal.py` | `transfer_purchase_to_proposal()` |

### Quantity Flow During Transfer

```python
# Source line (e.g., Proposal):
proposal_line.quantity = {"ordered": 5, ...}

# transfer_utils.convert_quantity_from_source() reads:
base = q.get("staged")     # None
base = q.get("ordered")    # 5  ← fallback
base = q.get("remaining")  # not reached

# Target line (Order) gets:
order_line.quantity = {
    "remaining": 5,
    "invoiced": 0,
    "converted_from_proposal": {
        "original_ordered": 5,
        "is_blanket": False
    }
}
# NOTE: No "staged" key set → extended = 0 on target too
```

### Inventory Impact (Pending Records)

When a line is saved, `update_inventory_on_save()` fires via signal and creates a `Pending` record:

| Transaction | Purpose | Inventory Bucket |
|-------------|---------|-----------------|
| Proposal | `inventory_line_add` | `on_p` (on proposal) |
| Order | `inventory_line_add` | `on_so` (on sales order) |
| Invoice | `inventory_line_add` | `on_in` (on invoice) |
| Purchase | `inventory_line_add` | `on_po` (on purchase order) |
| Work Order | `inventory_line_add` | `on_wo` (on work order) |

The `Pending → Item` processing flow is documented in `celery-redis-pending.md`. The Celery worker (or inline fallback) drains pending records and applies deltas to `Item.data.quantity`.

### Value Transfer

When converting between transaction types, the **value** (price, cost, extended) is copied from source to target:

```python
# build_line_payload() captures source data in refs['xfer']:
{
    "qty": {"base": 5, "staged": null, "ordered": 5},
    "price": {"unit": 721.0, "extended": 0.0},   # ← 0 because of bug
    "cost": {"unit": 345.6, "extended": 0.0}      # ← 0 because of bug
}
```

**Current state:** Because extended is 0 on every line, value transfers also carry 0. Fixing the quantity key mismatch will fix this cascadingly.

---

## File Map

| File | Role |
|------|------|
| `apps/transactions/models/base_line_model.py` | Model definitions, `_calculate_extended_price()`, `ensure_json_defaults()` |
| `apps/transactions/models/base_transaction_model.py` | Header model, `totals`/`sell`/`cost`/`finance` JSONB schemas |
| `apps/transactions/models/order.py` | `update_sell_cost_totals()` method on Order |
| `apps/transactions/services/order_totals.py` | `compute_order_sell_cost_totals()` aggregation |
| `apps/transactions/services/transaction_save.py` | `calculate_line_extended()`, `save_transaction_with_lines()` |
| `apps/transactions/services/line_item_service.py` | `LineItemService` CRUD, `_recalculate_line()` |
| `apps/transactions/signals.py` | Line post_save signals; totals signal only on ProposalLine |
| `apps/transactions/services/transfer_utils.py` | `convert_quantity_from_source()`, `build_line_payload()` |
| `apps/transactions/services/proposal_to_order.py` | Proposal → Order transfer |
| `apps/core/views/save_view.py` | Generic `/wcapi/save/` endpoint |
| `apps/transactions/services/pending_inventory_processor.py` | `process_line_item_pending()` — Pending → Item deltas |

---

## Fix Plan

### Fix 1: Quantity Key Normalization (Critical)

**Where:** `base_line_model.py` → `BaseLineCore.ensure_json_defaults()`

**What:** Add a `normalize_line_quantity()` function that maps `"ordered"` → `"staged"`, similar to the existing `normalize_price_map()` and `normalize_cost_map()`.

```python
def normalize_line_quantity(q: dict | None, transaction_type: str | None = None) -> dict:
    """Normalize quantity JSON: ensure 'staged' key exists."""
    base = default_quantity(transaction_type=transaction_type)
    if not isinstance(q, dict):
        return base

    out = dict(base)
    out.update(q)  # Overlay incoming keys onto defaults

    # Map "ordered" → "staged" if "staged" is missing or zero
    if not out.get("staged") and out.get("ordered"):
        out["staged"] = out.pop("ordered")
    elif "ordered" in out:
        out.pop("ordered")  # Remove redundant key

    return out
```

**Then update `ensure_json_defaults()`:**
```python
# Replace:
if not self.quantity:
    self.quantity = default_quantity(transaction_type=self._meta.model_name)

# With:
self.quantity = normalize_line_quantity(
    getattr(self, "quantity", None),
    transaction_type=self._meta.model_name
)
```

This fixes all save paths at once because every `line.save()` runs through `ensure_json_defaults()`.

### Fix 2: Header Totals Signal Registration (Critical)

**Where:** `signals.py` line 220

**What:** Register `update_totals_on_save` for all 5 line types, not just ProposalLine.

```python
# Replace:
register_line_totals_signals(ProposalLine, 'parent')

# With:
_TOTALS_CONFIG = [
    (ProposalLine,  'parent'),
    (OrderLine,     'order'),
    (InvoiceLine,   'invoice'),
    (PurchaseLine,  'purchase'),
    (WorkOrderLine, 'workorder'),
]

for _model, _parent_attr in _TOTALS_CONFIG:
    register_line_totals_signals(_model, _parent_attr)
```

### Fix 3: Transfer Quantity Output (Important)

**Where:** `transfer_utils.py` → `convert_quantity_from_source()` and `proposal_to_order.py` → `_convert_quantity_from_proposal()`

**What:** Ensure the output dict includes `"staged"` as the base quantity key:

```python
out = {
    "staged": base or 0,       # ← ADD THIS
    "remaining": base or 0,
    "invoiced": 0,
    converted_key: converted,
}
```

### Fix 4: Frontend Key Alignment (Optional, Lower Priority)

Optionally update React2025 to send `"staged"` instead of `"ordered"` in save payloads. This isn't strictly required because Fix 1 normalizes on the backend, but it eliminates the mismatch at the source. Affects ~8 files.

---

## Data Migration

### One-Time Fix for Existing Lines

After deploying Fix 1, all existing lines will self-correct on next save. But to fix them immediately:

```python
# management command: fix_quantity_keys
from apps.transactions.models import OrderLine, InvoiceLine, ProposalLine, PurchaseLine, WorkOrderLine

for Model in [OrderLine, InvoiceLine, ProposalLine, PurchaseLine, WorkOrderLine]:
    for line in Model.objects.all():
        q = line.quantity or {}
        if 'ordered' in q and not q.get('staged'):
            q['staged'] = q.pop('ordered')
            line.quantity = q
            line.save()  # triggers ensure_json_defaults → _calculate_extended_price
            # Also triggers header totals recalc (after Fix 2)
```

### Verification After Fix

```bash
DB_MODE=remote bin/python tools/audit_calcs.py
# Expected: 0 broken lines, header totals match line sums
```

---

## Related Documents

- [08-transaction-calculations.md](08-transaction-calculations.md) — Full calculation design reference (formulas, edge cases, API endpoints)
- [celery-redis-pending.md](celery-redis-pending.md) — Pending record processing architecture
- [ledger-financial-system.md](ledger-financial-system.md) — Invoice aging, payments, ledger records
- [inventory_flow_testing.md](inventory_flow_testing.md) — Inventory flow test procedures
