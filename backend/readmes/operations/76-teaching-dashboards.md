# Teaching Dashboards — Flow Visualization and Flight Simulators

## What They Are

Six dashboards built 2026-08-10/11 that teach how WebClerk works by showing
data in motion. Four are flow dashboards (show pipelines and conversion
rates). One is a flight simulator (step-by-step interactive training).
One is an operational tool that doubles as training (journal audit).

## The Six Dashboards

### 1. Sales Pipeline (`/sales-pipeline`)
**Teaches:** How selling actions connect to future outcomes.

Funnel: Actions → Proposals → Orders → Revenue

Each selling action carries an `impact` object:
- `predicted`: 1-5 gut feel at time of action
- `actual`: 1-5 looking back (Alice auto-fills, user corrects)
- `refs`: linked transactions + explanation

The gap between predicted and actual is the learning signal. Not precision
— retrospection. Alice guesses, users correct (2 seconds), Alice learns,
admin time drops.

**Action types:** call, email, visit, meeting, demo, marketing, referral,
social, event, follow_up, other.

**Calibration metrics:** avg_gap (positive = over-optimistic), correction_rate
(40% = learning, 10% = calibrated, 2% = trusted).

**Backend:** `apps/transactions/services/sales_pipeline.py`
**Manage action:** `get_sales_pipeline`

### 2. Cash Conversion (`/cash-conversion`)
**Teaches:** Where money stalls in the pipeline.

Stages: Order → Invoice → Payment → GL → Period Close

Each stage shows:
- Average days in stage
- Count stalled vs completed
- Dollar value stalled
- Alerts for records stalled > 30 days

Color thresholds: green < 7 days, yellow < 30, red >= 30.

Links to Journal Audit (`/journal-audit`) for GL exceptions.

**Backend:** `apps/accounts/services/cash_conversion.py`
**Manage action:** `get_cash_conversion`

### 3. Journal Audit (`/journal-audit`)
**Teaches:** How GL posting works and what can go wrong.

Three panels:
- **Queue** — transactions ready to post
- **Exceptions** — out-of-balance, can't post (requires user action)
- **Skipped** — hold, consigned, zero-amount (informational)

Key features:
- **Post Journals** button — runs `batch_journalize`, creates a JournalBatch record
- **ForceToBalance** — user writes statement (min 10 chars), system posts adjusting line
- **FX auto-absorption** — foreign currency residuals < $2 absorbed automatically
- Single-click shows detail, double-click opens in new tab

**JournalBatch model:** Header for every posting run. Stores totals, exception
count, absorption count, who ran it, when. The flight recorder for GL.

**Backend:** `apps/accounts/services/accounting_dashboard.py` (get_journal_exceptions),
`apps/accounts/services/journalize.py` (force_to_balance, batch_journalize)
**Manage actions:** `get_journal_exceptions`, `force_to_balance`, `batch_journalize`

### 4. Inventory Velocity (`/inventory-velocity`)
**Teaches:** Where capital is working vs parked.

Five views:
- **PO Exposure** — open POs by vendor (capital committed)
- **Receipt Performance** — avg days to receive, on-time % (vendor reliability)
- **On Hand Analysis** — ABC classification + margin velocity (stars vs dead capital)
- **Sales Velocity** — turns by category (what's moving)
- **Reorder Alerts** — items below reorder point with days-of-supply countdown

**Backend:** `apps/products/services/inventory_velocity.py`
**Manage action:** `get_inventory_velocity`

### 5. Flight Simulator: Inventory (`/flight-sim-inventory`)
**Teaches:** How inventory quantities, pending records, and GL entries change
at every stage of a transaction lifecycle.

Nine scripted steps:

| Step | Action | Inventory | GL |
|------|--------|-----------|-----|
| 1 | Starting inventory (100 units) | on_hand: 100 | — |
| 2 | Proposal for 15 | on_p: +15 | None |
| 3 | Convert 9 to Order | on_so: +9, on_p: -9 | None |
| 4 | Invoice 4 | on_hand: -4, on_so: -4 | AR $42 / Rev $40 / Tax $2 / COGS $24 / Inv $24 / Comm $2 |
| 5 | Purchase 14 | on_po: +14 | None |
| 6 | Receive 11 | on_hand: +11, on_po: -11 | Inv $66 / AP $66 |
| 7 | Partial payment $30 | — | Cash $30 / AR $30 |
| 8 | Discount $10 | — | Disc Exp $10 / AR $10 |
| 9 | Write-off $2 | — | Bad Debt $2 / AR $2 |

Config: 5% tax, 5% commission (easy mental math).

Invoice settlement: $42 = $30 cash + $10 discount + $2 write-off.
Margin waterfall: Revenue $40 → COGS $24 = Gross $16 (40%) → Commission $2
→ Discount $10 → Bad Debt $2 = **Net $2 (5%)**. This is why Alice tracks erosion.

Two modes:
- **Scripted** — `get_flight_scenario()` returns expected values per step
- **Live** — enter an item ID, `get_item_flight_state(item_id)` shows real data

**Backend:** `apps/products/services/inventory_flight_sim.py`
**Manage actions:** `get_flight_scenario`, `get_item_flight_state`

### 6. Accounting Dashboard (`/accounting`)
**Pre-existing.** Added a "Journal Exceptions" button that opens `/journal-audit`
in a new tab.

## Model Changes (2026-08-11)

| Model | Change | Migration |
|-------|--------|-----------|
| Action | Added `action_type` CharField (12 choices) | core 0037 |
| Action | Added `impact` JSONField (predicted/actual/refs) | core 0038 |
| JournalBatch | New model — GL posting run header | accounts 0019 |

## Onboarding Integration

Alice assigns flight simulator training as Action records in the new user's
weekly project. Six-item checklist:

1. Complete Flight Simulator: Inventory
2. Set impact.predicted on first 5 selling actions
3. Review Alice's auto-filled impact.actual on 3+ actions
4. View Sales Pipeline — find your conversion rate
5. View Cash Conversion — find stalled invoices
6. View Inventory Velocity — find dead capital

Soft gate — Alice prompts, doesn't block. Full details in `onboarding.md`.

## Flowcharts

- `readmes/flowcharts/wc3-flight-sim-inventory.dot/.pdf` — 9-step flow with GL
- `readmes/flowcharts/wc3-impact-assessment-loop.dot/.pdf` — Alice auto-populate cycle
- `readmes/flowcharts/wc3-inventory-buckets.dot/.pdf` — quantity flow through pending
- `readmes/flowcharts/wc3-all-flowcharts.pdf` — combined PDF, all 15 diagrams + intro

## Architecture

All dashboards follow the same pattern:
- Backend: Python service in `apps/*/services/` with a function returning a dict
- API: Lambda in `apps/core/views/manage_view.py` dispatching to the service
- Frontend: React TSX in `react-joint/src/pages/admin/` using `apiClient.post("/wcapi/manage/")`
- Route: registered in `Routes.ts` + `protectedRoutesConfig.tsx` + `AppSidebar.tsx`

| Dashboard | Service | React Component | Route |
|-----------|---------|-----------------|-------|
| Sales Pipeline | `sales_pipeline.py` | `SalesPipelineDashboard.tsx` | `/sales-pipeline` |
| Cash Conversion | `cash_conversion.py` | `CashConversionDashboard.tsx` | `/cash-conversion` |
| Journal Audit | `accounting_dashboard.py` + `journalize.py` | `JournalAuditDashboard.tsx` | `/journal-audit` |
| Inventory Velocity | `inventory_velocity.py` | `InventoryVelocityDashboard.tsx` | `/inventory-velocity` |
| Flight Sim: Inventory | `inventory_flight_sim.py` | `InventoryFlightSim.tsx` | `/flight-sim-inventory` |

## The Principle

The trail must be packed before it's open. A feature not trained is a feature
not used. Flight simulators are how we pack the trail.

Not precision, but retrospection. The numbers are waffly. The value is in
coming back, seeing the gap, and asking why.
