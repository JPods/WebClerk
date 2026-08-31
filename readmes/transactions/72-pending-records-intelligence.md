# Pending Records — Strategic Intelligence from Intent
**Created:** 2026-08-09
**Owner:** Alice (archival, pattern extraction, coaching signals)

---

## The Insight

Every exchange of inventory and cash in WC3 passes through a pending record before it becomes real. That pending record captures **intent** — what was requested, when, by whom, for what item, at what price. Intent is more valuable than outcome for pattern analysis because it includes the attempts that were canceled, the timing before action, and the demand signal before supply responds.

Most systems discard pending records after processing. That's throwing away the richest signal in the business.

**The problem:** Keeping every pending record in the operational database creates noise — high write volume, slow queries, bloated storage.

**The solution:** Archive processed pending records to external dated storage. Load into collections for trend, cycle, volatility, and process health analysis by product class and cash flow category. The noise leaves the database. The patterns stay forever.

Flowchart: `readmes/flowcharts/wc3-pending-records.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-pending-records.dot -o readmes/flowcharts/wc3-pending-records.pdf
```

---

## The Three Pending Models

| Model | What it captures | State lifecycle |
|-------|-----------------|----------------|
| **PendingInventoryAdjustment** | Every inventory intent — receive, ship, count adjust, transfer, BOM consumption | pending → applied → archived *or* canceled → archived |
| **PendingPaymentApplication** | Every cash flow intent — customer payment, vendor payment, invoice application | pending → applied → archived *or* canceled → archived |
| **Pending** (generic queue) | Everything else — layout saves, sync bundles, deferred processing | created → processed → archived |

All three follow the same pattern: **intent recorded → worker processes → state updated → archive extracts**.

### What Makes Pending Records Valuable

| Field | What it reveals |
|-------|----------------|
| **dt_created → dt_applied** | Processing latency — how long intent waits before becoming action |
| **state=canceled + cancel_reason** | Failed intent — why demand or payment didn't convert |
| **request_ref** | Who requested it, from what context (API, UI, sync, Alice) |
| **qty / amount** | Volume and value of intent — demand signal before fulfillment |
| **item / invoice linkage** | What was being moved or paid — product class and cash flow category |

---

## The Lifecycle

```
Business Event (intent)
    │
    ▼
Pending Record created (operational DB)
    │  state = pending
    │  captures: who, what, when, why, how much
    │
    ▼
Celery Worker processes
    │  Inventory: drain every 30s (adaptive)
    │  Payment: apply to invoice, create ledger entry
    │  Generic: model-specific logic
    │
    ├── state = applied → InventoryMovement / PaymentApplication / Ledger
    │
    └── state = canceled → cancel_reason recorded
    │
    ▼
Alice Archive Task (nightly)
    │  Extract intent data + timing + outcome
    │  Write to dated external file
    │  Soft-delete from operational DB
    │
    ▼
External Archive (dated_outside/)
    │  Compressed JSONL by product class / cash category / month
    │
    ▼
Pattern Analysis (load into collections)
    │  Trends, cycles, volatility, process health, forecasts
    │
    ▼
Feedback to Operations
    inventory_min/max, cash reserves, reorder timing,
    collection priority, seasonal staffing
```

---

## External Archive — Folder Structure

```
.local/dated_outside/
├── inventory/
│   ├── {product_class}/          # e.g., fasteners/, electronics/, apparel/
│   │   ├── 2026-01.jsonl.gz
│   │   ├── 2026-02.jsonl.gz
│   │   └── ...
│   └── _unclassified/
│       └── 2026-08.jsonl.gz
├── cash_flow/
│   ├── customer_receipts/
│   │   └── 2026-08.jsonl.gz
│   ├── vendor_payments/
│   │   └── 2026-08.jsonl.gz
│   ├── applied_to_invoice/
│   │   └── 2026-08.jsonl.gz
│   └── _unclassified/
│       └── 2026-08.jsonl.gz
└── queue/
    ├── {model_name}/             # e.g., layout/, sync/, document/
    │   └── 2026-08.jsonl.gz
    └── _unclassified/
        └── 2026-08.jsonl.gz
```

**Format:** JSONL (one JSON object per line), gzipped by month. JSONL allows append-only writes and line-by-line streaming reads — no need to parse the entire file.

**Naming:** `YYYY-MM.jsonl.gz` — one file per month per category. Monthly granularity balances file count against file size.

**Retention:** Raw archive files kept indefinitely (storage is cheap, patterns are priceless). Aggregated summaries in ItemUsage monthly metrics are the operational view.

### Archive Record Schema

```json
{
    "dt_created": 1723200000000,
    "dt_applied": 1723200030000,
    "processing_ms": 30000,
    "state": "applied",
    "type": "inventory",
    "item_id": 456,
    "item_sku": "WIDGET-100",
    "product_class": "fasteners",
    "warehouse_id": 1,
    "qty": 50.0,
    "reason": "po_receipt",
    "request_ref": {"source": "sync", "bundle_id": 42},
    "cancel_reason": null
}
```

---

## What the Patterns Reveal

### Inventory Patterns

| Analysis | What it shows | Business value |
|----------|-------------|---------------|
| **Demand trend** | Slope of monthly demand by product class | Is demand growing, flat, or declining? Adjust inventory_min. |
| **Seasonal cycles** | Monthly peaks and valleys over 12+ months | Pre-position inventory before Q4 rush. Reduce before slow periods. |
| **Volatility (CV)** | Coefficient of variation by product class | Feeds adaptive window for inventory_min/max calculation. High CV = shorter window. |
| **Lead time trend** | Gap between PO pending and receipt applied | Vendor reliability — are lead times growing? Time to find alternatives. |
| **Cancellation patterns** | Why pending adjustments were canceled | Process problems — canceled because already adjusted? Because count was wrong? |
| **BOM consumption rhythm** | Component demand driven by assembly schedules | Production planning — when do assemblies consume components? |

### Cash Flow Patterns

| Analysis | What it shows | Business value |
|----------|-------------|---------------|
| **Revenue seasonality** | When customer payments concentrate | Q4 concentration → plan Q1 cash reserves |
| **Payment timing** | Days from invoice to payment pending to applied | Collection effectiveness — are customers paying slower? |
| **AP scheduling** | When vendor payments are applied | Cash outflow rhythm — avoid clustering payments in one week |
| **Discount capture** | How often early-payment discounts are taken | Free money being left on the table? |
| **Aging acceleration** | Trend in days-to-apply over time | Early warning: aging is getting worse before the AR report shows it |
| **Cash conversion cycle** | Inventory pending → sale → invoice → payment | The full cycle — where is cash stuck? |

### Process Health

| Analysis | What it shows | Business value |
|----------|-------------|---------------|
| **Pending→applied conversion rate** | What % of intent becomes action | Low rate = bottleneck or validation failures |
| **Processing latency** | How long pending records wait | Growing latency = system under stress or worker falling behind |
| **Stale pending rate** | Records stuck > threshold | Operational problem — something is blocked |
| **Cancellation rate by reason** | Why intent fails | Process improvement target — fix the top cancellation reason |
| **Attempt count distribution** | How many retries before success | Infrastructure health — high retries = intermittent failures |

---

## Service Functions Needed

| Function | Module | What it does |
|----------|--------|-------------|
| `archive_processed_pending()` | `apps/support/services/pending_archive.py` | Celery nightly: extract applied/canceled pending records, write to dated_outside, soft-delete from DB |
| `load_archive_collection(type, product_class, start, end)` | `apps/support/services/pending_analysis.py` | Load archived JSONL files into memory for analysis — returns list of dicts |
| `compute_demand_trend(product_class, months)` | `apps/support/services/pending_analysis.py` | Slope and direction of demand from inventory archives |
| `detect_seasonal_cycle(product_class, min_months)` | `apps/support/services/pending_analysis.py` | Find repeating monthly patterns — peak months, valley months |
| `compute_volatility(product_class, months)` | `apps/support/services/pending_analysis.py` | CV and std dev for adaptive window calculation |
| `compute_cash_flow_seasonality(category, months)` | `apps/support/services/pending_analysis.py` | Monthly cash flow pattern — where revenue concentrates |
| `compute_conversion_rates(type, months)` | `apps/support/services/pending_analysis.py` | Pending→applied rate by type — process health signal |
| `compute_processing_latency(type, months)` | `apps/support/services/pending_analysis.py` | Avg and trend of processing time — infrastructure health |
| `flag_pattern_changes(product_class)` | `apps/support/services/pending_analysis.py` | Alice coaching: detect when an item's pattern shifts band (stable→volatile) |

### Celery Tasks

| Task | Schedule | What it does |
|------|----------|-------------|
| `alice_archive_pending` | Nightly 1:00 AM | Archive processed pending records to dated_outside |
| `alice_pending_patterns` | Weekly Mon 3:00 AM | Run pattern analysis on archived data, update ItemUsage metrics |
| `alice_cash_flow_patterns` | Weekly Mon 3:30 AM | Cash flow seasonality analysis, update coaching signals |

---

## The Seasonal Business Case

A business that gets 60% of revenue in Q4:

**Without pending analysis:**
- Q4 arrives, inventory runs out, rush orders at premium cost
- Q1 arrives, cash crunch because revenue dried up but expenses didn't
- Every year the same surprise

**With pending analysis:**
- October: pending payment volume trending 3× above Q3 average → signal confirmed
- Alice recommends: inventory_max increase for top 20 product classes by November 1
- December: pending payment application volume declining → Q4 peak passing
- Alice recommends: cash reserve target for Q1 based on trailing 3-year Q1 cash flow pattern
- January: no surprise — reserves were built, inventory was right-sized

The pending records saw it coming because they captured the intent before the action.

---

## Connection to Inventory Bounds

The adaptive window in `inventory_bounds.py` uses CV (coefficient of variation) to select trailing months. That CV calculation currently reads from ItemUsage monthly metrics. With the pending archive:

1. **ItemUsage** stores the monthly summary (fast, operational)
2. **Pending archive** stores the raw intent data (detailed, analytical)
3. **Pattern analysis** enriches ItemUsage with trend/cycle/volatility from archive data
4. **Inventory bounds** reads enriched ItemUsage for adaptive window selection

The archive is the deep memory. ItemUsage is the operational view. The recommender reads the operational view. Alice keeps both in sync.

---

## Files

| File | What it is |
|------|-----------|
| `apps/support/services/pending_archive.py` | Archive service — extract, write, soft-delete (to be created) |
| `apps/support/services/pending_analysis.py` | Pattern analysis — trend, cycle, volatility, process health (to be created) |
| `apps/products/models/inventory_layer.py` | PendingInventoryAdjustment model |
| `apps/transactions/models/pending_payment.py` | PendingPaymentApplication model |
| `apps/core/models/pending.py` | Pending generic queue model |
| `apps/products/services/inventory_bounds.py` | Consumes volatility data for adaptive window |
| `.local/dated_outside/` | External archive folder (to be created) |
| `readmes/flowcharts/wc3-pending-records.dot` | Visual pipeline diagram |

## Related

| Readme | Connection |
|--------|-----------|
| `readmes/71-products-item-support.md` | Products app architecture — where inventory pending lives |
| `readmes/69-celery-architecture.md` | Celery task registry — where archive/analysis tasks go |
| `readmes/flowcharts/wc3-inventory-buckets.dot` | How pending drains into inventory buckets |
| `readmes/flowcharts/wc3-payment-gl.dot` | How payment pending flows to GL |
