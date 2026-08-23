# AI Calculation Audit — r25 vs wc3 Discrepancy Detection

> **Date:** 2026-03-07
> **Status:** ✅ Implemented
> **Service:** `apps/accounts/services/ai_audit.py`
> **Model:** `accounts.Audit` (table: `audits`)

---

## Purpose

The browser is an untrusted client. r25 (React frontend) computes line
extended prices and quantity envelopes optimistically for instant UI
feedback.  wc3 (Django backend) is the **authoritative recalculator** —
it always recomputes extended values on save via
`_calculate_extended_price()` and normalizes quantities via
`normalize_quantity_map()`.

This audit service detects when r25's submitted values disagree with
wc3's recalculation beyond a rounding tolerance.  Discrepancies are:

1. **Logged** via Python `logging` (logger: `ai_audit`)
2. **Persisted** to the `accounts.Audit` model for trending and review
3. **Never block** the save path — all audit code is wrapped in try/except

---

## What Gets Audited

### 1. Extended Price Audit (`ai_calculation_audit`)

Runs inside `BaseSellLineModel._calculate_extended_price()` on every
sell-side line save (proposal, order, invoice).

| Check | Formula | Tolerance |
|-------|---------|-----------|
| `price.extended` | `qty.staged × price.unit − discount_amount` | $0.02 |
| `cost.extended` | `qty.staged × cost.unit − discount_amount` | $0.02 |

**Flow:**
1. Snapshot r25-submitted `price.extended` and `cost.extended`
2. Run wc3's authoritative calculation (overwrites the values)
3. Compare submitted vs calculated
4. If delta > tolerance → log + create Audit record

### 2. Quantity Consistency Audit (`ai_quantity_audit`)

Runs inside `BaseLineCore.ensure_json_defaults()` on every line save
(all transaction types).

| Check | Rule | Tolerance |
|-------|------|-----------|
| Remaining consistency | `remaining = active − children_active.sum` (= `active` when no children) | 0.001 |
| Standalone mirroring | If `active` set but `staged = 0`, normalization mirrors `staged = active` | 0.001 |

---

## Audit Record Structure

Each discrepancy creates an `accounts.Audit` record:

```python
Audit(
    purpose="ai_calculation_audit",  # or "ai_quantity_audit"
    name="order line 10: price.extended",
    conflicts={
        "discrepancies": [
            {
                "field": "price.extended",
                "submitted": 100.50,    # what r25 sent
                "calculated": 100.00,   # what wc3 computed
                "delta": 0.50,
                "tolerance": 0.02,
                "line_model": "order_line",
                "line_id": 42,
                "parent_id": 17,
            }
        ],
        "context": {
            "line_model": "order_line",
            "line_id": 42,
            "line_number": 10,
            "transaction_id": 17,
            "transaction_model": "order",
            "item_id": 243,
            "item_code": "WIDGET-A",
        }
    },
    changes={
        "price.extended": {"from": 100.50, "to": 100.00}
    },
    recommendations={
        "source": "ai_audit",
        "severity": 1,
        "check": "r25 lineItemService.calculateLine() vs wc3 _calculate_extended_price()",
        "fields": ["price.extended"],
    },
    rating=1,           # 0=info, 1=warning, 2=error
    is_completed=True,  # auto-resolved: wc3 applied its value
    priority=1,
    refs={
        "links": {
            "transaction": [{"model": "order", "id": 17}],
            "line": [{"model": "order_line", "id": 42}],
            "item": [{"id": 243, "code": "WIDGET-A"}],
        },
        "keywords": ["ai_audit", "ai_calculation_audit"],
        "tags": ["ai_calculation_audit"],
    },
)
```

---

## Configuration

Constants in `apps/accounts/services/ai_audit.py`:

| Constant | Default | Purpose |
|----------|---------|---------|
| `PRICE_TOLERANCE` | `Decimal("0.02")` | Max acceptable price delta |
| `QUANTITY_TOLERANCE` | `Decimal("0.001")` | Max acceptable quantity delta |
| `WRITE_AUDIT_RECORDS` | `True` | Set `False` to log-only (no DB writes) |

---

## Code Path Index

| File | Function | What it does |
|------|----------|-------------|
| `apps/accounts/services/ai_audit.py` | `check_extended_prices()` | Compares price/cost extended |
| `apps/accounts/services/ai_audit.py` | `check_quantity()` | Validates quantity envelope consistency |
| `apps/accounts/services/ai_audit.py` | `_log_and_persist()` | Logs + creates Audit record |
| `apps/transactions/models/base_line_model.py` | `_calculate_extended_price()` | Calls `check_extended_prices()` after recalc |
| `apps/transactions/models/base_line_model.py` | `ensure_json_defaults()` | Calls `check_quantity()` after normalization |

### r25 counterparts (should produce identical results)

| File | Function |
|------|----------|
| `src/apps/transactions/services/lineItemService.ts` | `calculateLine()` |
| `src/apps/transactions/services/lineItemService.ts` | `updateQuantity()` |
| `src/apps/transactions/services/lineItemService.ts` | `getDefaultQuantity()` |
| `src/apps/transactions/components/LinesCard.tsx` | `applyFieldUpdate("qty")` |

---

## Querying Audit Records

```python
from apps.accounts.models.audit import Audit

# All calculation discrepancies
Audit.objects.filter(purpose="ai_calculation_audit")

# All quantity discrepancies
Audit.objects.filter(purpose="ai_quantity_audit")

# Discrepancies for a specific transaction
Audit.objects.filter(
    purpose__startswith="ai_",
    refs__links__transaction__contains=[{"model": "order", "id": 17}],
)

# High severity only
Audit.objects.filter(purpose__startswith="ai_", rating__gte=2)

# Recent discrepancies (last 7 days)
from django.utils import timezone
from datetime import timedelta
week_ago = int((timezone.now() - timedelta(days=7)).timestamp() * 1000)
Audit.objects.filter(purpose__startswith="ai_", dt_created__gte=week_ago)
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Audit in `_calculate_extended_price()` not `save()` | Captures the exact moment of recalculation, not general save lifecycle |
| `accounts.Audit` model, not `core.AuditLog` | AuditLog tracks user actions (CRUD). Audit tracks system analysis (conflicts, recommendations) — fits the AI audit pattern |
| `try/except` wrapper | Audit is observational — a failed audit record must never block a sale |
| Tolerance-based comparison | Floating-point rounding differences between JS and Python are expected; only flag meaningful divergence |
| `is_completed=True` | wc3 auto-resolved by applying its own value — the record is for observation, not action |

---

## Relationship to Other AI Tasks

This is part of the **Phase 5 — Autonomous Data Intelligence** suite:

| Task | Service | Relationship |
|------|---------|-------------|
| 5E Health Scoring | `health_scorer.py` | Audit discrepancies could lower a line's health score |
| 5F Margin Tracking | `margin_tracker.py` | Margin drift might correlate with price calculation bugs |
| 5D Schema Drift | `schema_drift_detector.py` | Type mismatches between r25/wc3 could cause calculation divergence |
| **5I Calculation Audit** | **`ai_audit.py`** | **This feature** — detects r25 vs wc3 calculation discrepancies |
