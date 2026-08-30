# Erosion Tracking System

## Overview

The erosion system captures every event where value is lost between transaction stages — margin compression, late-payment carrying costs, discounting, FX losses, rework, and more. It gives Alice (the analysis subagent) a structured dataset for pattern detection and cash-flow projection.

Every erosion record answers: **how much money did we leave on the table, where did it happen, and who was involved?**

## Implementation Files

| File | Purpose |
|------|---------|
| `apps/accounts/models/erosion.py` | Erosion model |
| `apps/accounts/choices.py` | `EROSION_CATEGORY_CHOICES`, `EROSION_SOURCE_MODEL_CHOICES` |
| `apps/accounts/services/erosion.py` | Detection functions + summary reporting |
| `apps/transactions/services/transaction_save.py` | Phase 6 — margin & discount erosion on invoice/order save |
| `apps/transactions/signals.py` | Late-payment erosion on Payment post_save |
| `apps/accounts/tests/test_erosion.py` | 10 tests across 4 test classes |

---

## Erosion Model

**Table:** `erosion`  
**Inherits:** `BaseModel` (provides `id`, `dt_created`, `dt_modified`, `metadata`)

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `category` | CharField(50) | Indexed. One of the 10 erosion categories. |
| `amount` | DecimalField(12,2) | **Always positive** — represents value lost. |
| `amount_pct` | DecimalField(8,4) | Nullable. Percentage erosion (0.11 = 11 margin points). |
| `org` | FK → `OrgBase` | Customer or vendor associated. Nullable, SET_NULL. |
| `contact` | FK → `Contact` | Rep or salesperson responsible. Nullable, SET_NULL. |
| `source_model` | CharField(50) | Transaction type where erosion was detected. |
| `source_id` | BigIntegerField | PK of the source transaction. Indexed. |
| `parent_model` | CharField(50) | Ancestor transaction type being compared against. Nullable. |
| `parent_id` | BigIntegerField | PK of the parent/comparison transaction. Nullable, indexed. |
| `dt_event` | DateTimeField | When the erosion event occurred. |
| `notes` | TextField | Free-text explanation. |
| `is_auto` | BooleanField | `True` = auto-calculated during pipeline, `False` = manual entry. |

### Indexes

| Name | Fields | Purpose |
|------|--------|---------|
| `idx_erosion_org_cat` | `(org, category)` | Fast lookup by customer + erosion type |
| `idx_erosion_org_date` | `(org, dt_event)` | Time-range queries per customer |
| `idx_erosion_source` | `(source_model, source_id)` | Find erosion for a specific transaction |

### Source / Parent Model Choices

`source_model` and `parent_model` accept the same set of values:

| Value | Label |
|-------|-------|
| `proposal` | Proposal |
| `order` | Order |
| `invoice` | Invoice |
| `purchase` | Purchase |
| `payment` | Payment |
| `credit_memo` | Credit Memo |
| `action` | Action |
| `question_answer` | Question / Answer |

This naming convention (`parent_model` / `parent_id`) matches `TransactionBaseModel` and `Ledger`.

### Sign Convention

`amount` is **always positive**. It represents the dollar value of value lost. A $200 margin drop is recorded as `amount = 200.00`, not `-200.00`.

---

## Categories

| Category | Code | Auto? | Description |
|----------|------|-------|-------------|
| Margin | `margin` | ✅ | Invoice margin < ancestor proposal/order margin |
| Discount | `discount` | ✅ | Discount applied at transaction level |
| Late Payment | `late_payment` | ✅ | Payment received past ledger due date (carrying cost) |
| FX Loss | `fx_loss` | ❌ | Currency conversion loss |
| Return/Credit | `return_credit` | ❌ | Value lost to returns or credit memos |
| Rework | `rework` | ❌ | Cost of re-doing work |
| Shipping | `shipping` | ❌ | Excess or unrecovered shipping costs |
| Bad Debt | `bad_debt` | ❌ | Uncollectable receivables |
| Price Override | `price_override` | ❌ | Manual price reductions below list |
| Other | `other` | ❌ | Catch-all for miscellaneous erosion |

---

## Pipeline Integration

### Phase 6 — Invoice/Order Save (`transaction_save.py`)

After the ledger records are created in Phase 5, Phase 6 runs erosion detection:

```
Phase 1: Lines → update totals
Phase 2: Header → update header fields
Phase 3: Consolidation → consolidate inventory
Phase 4: Status → sync status
Phase 5: Ledger → create/update ledger records
Phase 6: Erosion → detect margin & discount erosion     ← NEW
```

**Guarded by:** `model_key in ('invoice', 'order')`

Calls:
- `detect_margin_erosion(header_obj)` — walks parent chain, compares margins
- `detect_discount_erosion(header_obj)` — captures standalone discount amounts

### Payment Signal (`signals.py`)

After `on_payment_save()` creates/updates ledger records, the `create_payment_ledger` signal handler calls:

- `detect_late_payment(instance)` — compares payment date vs earliest unpaid ledger due date

Both pipeline hooks are wrapped in `try/except` to prevent erosion failures from blocking the main save.

---

## Chain Walk — How Margin Erosion Works

The `_get_ancestor_chain()` function walks the `parent_id` / `parent_model` fields upward from the source transaction:

```
Invoice #100  (parent_model='order', parent_id=50)
  └→ Order #50  (parent_model='proposal', parent_id=25)
       └→ Proposal #25  (no parent)
```

For each ancestor found, `detect_margin_erosion()` compares `totals.margin`:

1. If invoice margin ($800) < order margin ($1,000), record $200 erosion against the order.
2. If invoice margin ($800) < proposal margin ($1,200), record $400 erosion against the proposal.

### Cycle Protection

The chain walker uses `(model_name, id)` tuples for cycle detection. This prevents infinite loops and correctly handles the case where different transaction tables share the same auto-increment PK values (e.g., Order #1 and Proposal #1 are different records).

### Idempotency

All auto-detection functions delete existing auto records for the same source+parent pair before creating new ones. Re-saving an invoice recalculates erosion from scratch.

---

## Late Payment Carrying Cost

`detect_late_payment(payment)` calculates the cost-of-capital penalty when a customer pays past the due date:

```
carrying_cost = payment_amount × daily_rate × days_late
```

**Default daily rate:** 0.05% (≈ 18% annualized)

Example: $5,000 payment arriving 15 days late:
```
$5,000 × 0.0005 × 15 = $37.50 carrying cost
```

The function finds the earliest unpaid ledger record (`is_settled=False`) for the invoice and uses its `dt_due` as the benchmark.

---

## Summary / Reporting

```python
from apps.accounts.services.erosion import get_org_erosion_summary

summary = get_org_erosion_summary(org_id=42, days=90)
# Returns:
# {
#     'total': Decimal('1234.56'),
#     'count': 15,
#     'by_category': {
#         'margin': Decimal('800.00'),
#         'late_payment': Decimal('234.56'),
#         'discount': Decimal('200.00'),
#     },
#     'period_days': 90,
# }
```

---

## Test Coverage

**File:** `apps/accounts/tests/test_erosion.py`  
**Tests:** 10 across 4 classes

| Class | Tests | What it covers |
|-------|-------|----------------|
| `TestMarginErosion` | 5 | Basic margin drop, no-parent case, no-erosion-if-margin-same, zero-total skip, full chain walk (proposal → order → invoice) |
| `TestLatePaymentErosion` | 2 | Late payment carrying cost calculation, on-time payment produces no erosion |
| `TestDiscountErosion` | 2 | Discount recorded as erosion, zero discount produces no erosion |
| `TestOrgErosionSummary` | 1 | Aggregation by category with correct totals |

```bash
python -m pytest apps/accounts/tests/test_erosion.py -v
```

---

## Future — Alice Integration

The erosion table gives Alice structured data to:

1. **Identify chronic margin compression** — customers who consistently erode margins from proposal to invoice
2. **Score payment behavior** — customers with repeated late-payment erosion
3. **Project cash flow impact** — forecast carrying costs based on historical patterns
4. **Flag discount abuse** — customers where discounting is the dominant erosion category
5. **Recommend pricing adjustments** — suggest margin buffers for customers with high erosion rates

The `get_org_erosion_summary()` function is the starting point for Alice's erosion analysis. Future work will add trending (month-over-month), percentile ranking across the customer base, and alert thresholds.

---

## Metadata Annotations (`metadata.erosions` / `metadata.small_stings`)

Every `BaseModel` descendant carries two erosion-related arrays in its `.metadata` JSONField:

```json
{
  "metadata": {
    "small_stings": [
      {"category": "discount", "amount": 12.50, "dt": 1741392000000, "note": "Loyalty discount applied"}
    ],
    "erosions": [
      {"category": "margin", "amount": 200.00, "dt": 1741392000000, "note": "Margin dropped from proposal"}
    ]
  }
}
```

| Array | Purpose | Typical entries |
|-------|---------|----------------|
| `small_stings` | Minor customer-base erosions — small losses that accumulate | Discounts, rounding, price overrides, shipping adjustments |
| `erosions` | Significant erosion events worth individual attention | Margin compression, late payment costs, rework, bad debt |

These arrays provide **immediate per-record visibility** without querying the `erosion` table. The `erosion` table remains the consolidated, queryable history for reporting and Alice analysis.

Each entry shape: `{"category": str, "amount": float, "dt": ms_epoch, "note": str}`

The arrays are initialized empty by `default_metadata()` and ensured by `_init_metadata_if_needed()`.
