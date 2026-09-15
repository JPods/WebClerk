# WC2 Tally Methods Migration Plan

## Goal
Migrate WC2 Tally behavior into wc3 services and wcapi/report endpoints with functional parity first, then architecture cleanup.

## Scope
- Source system: WC2 methods in Methods/ where name starts with Tally
- Migration target: wc3 services under:
  - apps/accounts/services/
  - apps/core/services/
  - apps/core/views/
  - apps/products/services/
  - apps/transactions/services/
- Out of scope for phase 1:
  - UI parity in legacy dialogs
  - legacy script runner behavior (ExecuteTallyMaster*) beyond report execution compatibility

## Inventory Summary
- Total Tally-prefixed methods discovered: 52
- High-impact aggregation methods:
  - TallySummaryByPeriod.4dm
  - TallyMonthlyUsage.4dm
  - Tally_dInvent.4dm
  - TallySalesByMfrByMonth.4dm
  - TallySalesByCustomerByMonth.4dm
  - TallyPastDueLoo.4dm
- Orchestration/report methods:
  - TallyMaster*
  - TallyResult*
  - TallyCreate.4dm, TallyCalc.4dm, Tally_SaveCalc.4dm

## Functional Buckets

### 1) Period Summary and KPI Tallies
Primary source:
- TallySummaryByPeriod.4dm

Behavior:
- Date-bounded rollups for invoices, orders, proposals, purchases, leads, service, and call reports
- Produces amount/cost/tax/shipping/count style arrays and totalized period metrics

wc3 target:
- New read service under apps/core/services/ returning structured summary object
- Optional persisted report rows in apps/core/models/report.py payload patterns

### 2) Inventory and Usage Tallies
Primary source:
- TallyMonthlyUsage.4dm
- Tally_dInvent.4dm
- TallyInventoryProcess.4dm
- TallyYearlyUsageSum.4dm

Behavior:
- Consumes inventory movement events and computes month/year usage metrics (qty, value, turns, adjustments, scrap, margins)

wc3 target:
- Service in apps/products/services/ that aggregates inventory movements from transaction lines and item quantity snapshots
- Optional materialized monthly usage table or report cache for fast reads

### 3) Sales by Customer / Manufacturer / Time
Primary source:
- TallySalesByMfrByMonth.4dm
- TallySalesByCustomerByMonth.4dm
- TallySalesByYearByCustomer.4dm
- TallyCustSaleMo.4dm
- TallyVendSaleMo.4dm

Behavior:
- Monthly/yearly sales breakdown by customer and manufacturer dimensions

wc3 target:
- Reporting service in apps/core/services/ with grouped aggregate queries
- Endpoint exposure through wcapi manage/query actions

### 4) Receivables and Past-Due Tallies
Primary source:
- TallyPastDueLoo.4dm
- plus Ledger_TallyBal.4dm dependency

Behavior:
- Customer-by-customer receivable aging and past-due rollups

wc3 status:
- Existing aging endpoint in apps/core/views/manage_view.py (get_receivable_aging)

wc3 target:
- Extend/normalize output to cover parity fields expected by WC2 reports
- Add service wrapper so aging logic is reusable by report jobs

### 5) TallyMaster Script and Result Infrastructure
Primary source:
- TallyMasterExecutePopup.4dm
- TallyMasterExecuteSort.4dm
- TallyMastersExecuteSearch.4dm
- TallyMasterRecordsToText*.4dm
- TallyResult.4dm, TallyResultsiLo.4dm

Behavior:
- Method discovery, scripted execution, result persistence/export

wc3 target:
- Map to report registry + explicit service methods instead of dynamic script text execution
- Keep export compatibility via structured CSV/JSON report outputs

## Migration Strategy (Phased)

### Phase 0: Baseline and Contracts
- Freeze representative WC2 outputs for sample periods and entities
- Define parity contracts per report (inputs, groupings, metrics, output fields)
- Build fixture datasets in wc3 tests for deterministic comparisons

Deliverables:
- Parity spec document per tally family
- Test fixture seed set

### Phase 1: Receivables + Period Summary (Highest Value)
Implement first:
- Past due / receivable parity layer
- Summary-by-period rollup service

Why first:
- Direct accounting visibility
- Existing wc3 aging foundation already present

Tests:
- Service-level aggregate assertions
- Endpoint envelope and field-level parity checks

### Phase 2: Sales Dimension Tallies
Implement:
- Sales by customer by month
- Sales by manufacturer by month
- Year-over-year customer sales

Tests:
- Grouping accuracy (customer/mfr/month/year)
- Monetary totals and count parity against fixtures

### Phase 3: Inventory Usage Tallies
Implement:
- dInventory-based monthly usage calculations
- Yearly usage summary and valuation metrics

Tests:
- Quantity/value movement parity
- Edge cases: returns, voids, adjustments, negative movement

### Phase 4: TallyMaster Compatibility Layer
Implement:
- Named report execution registry (no dynamic script eval)
- Export endpoints replacing RecordsToText* paths

Tests:
- Execution routing and parameter validation
- Stable export schema

## Data Model and Service Design Notes
- Prefer pure read services for aggregate computations first
- Use temporary in-memory collections for most report assembly (compute by default)
- Persist only when there is legal, fiscal, audit, or operational replay value
- Keep API envelope compliance for all new endpoints
- Use canonical naming only (order, purchase, order_line, purchase_line)
- Avoid legacy name leakage in new code

## Report Persistence Strategy (Authoritative)

### Default behavior
- Do not recreate broad TallyResult-style storage for routine reports
- Build report outputs from transactional records and JSON object fields at request/run time
- Treat WC2 tally methods as feature references, not implementation templates

### Persisted fiscal/audit history (required)
- Obligated fiscal history is persisted in accounting and audit domains
- Use accounts/audit records for durable financial traceability and review
- Financial postings, balance-affecting events, and compliance-relevant history must be reproducible from persisted records

### Hard snapshots outside primary DB (allowed and preferred)
- For non-fiscal hard snapshots (large exports, point-in-time report artifacts), write immutable files to external storage
- Store a pointer/reference path in a docs/document record (plus metadata such as report key, period, checksum/hash, and creator)
- This keeps the operational database lean while preserving durable artifacts when needed

### Optional `core/results` table (only if justified)
- Create a general `core/results` accumulator only when one or more of these become true:
  - repeated expensive recomputation materially impacts runtime
  - required scheduled snapshots need fast retrieval
  - strict reproducibility/versioning is required across many report families
  - cross-domain analytics cannot be cleanly owned by accounts/audit/docs
- If created, keep it minimal and generic: `result_key`, `scope_hash`, `period_start`, `period_end`, `computed_at`, `status`, `payload`, `lineage`

### Decision rule
- Compute by default
- Persist by obligation or measurable performance need

## Alice Subagent Integration (Help and Adoption)

### Purpose
- Include Alice subagent in the reporting rollout so we can observe how users run report functions and where they need guidance
- Use those observations to design in-product help, smarter defaults, and workflow hints

### What Alice should capture
- report function invoked (report key/action)
- filter context (date range, entity scope, grouping choices)
- execution outcome (success, fail, timeout, empty-result)
- user flow markers (re-runs, filter changes, export actions)
- help-touchpoints (opened help, dismissed tips, followed suggestion)

### Where to store this
- lightweight operational telemetry in core/activity logs for product improvement
- obligated financial/fiscal history remains in accounts/audit only
- large or durable report artifacts remain external, with docs/document pointers
- short-lived contextual snippets may be stored in `metadata.temp[]` with required `clear_dt` timestamps
- Celery performs automatic cleanup of expired `metadata.temp[]` entries to prevent record clutter

### Help features Alice can drive
- contextual explanations for each report metric and grouping
- "why is this empty" guidance based on selected filters
- recommended next filters based on common user paths
- alerting for common configuration mistakes (date boundaries, missing entity scope)
- report-specific quick-start checklists and inline examples

### Guardrails
- avoid storing sensitive payload bodies unless required
- prefer aggregate usage metadata over raw record content
- keep audit/compliance storage separate from UX telemetry
- all user-facing help suggestions must be explainable and deterministic
- every `metadata.temp[]` entry must include an explicit `clear_dt` (epoch ms)
- entries without valid `clear_dt` are treated as stale and removed by cleanup

### Rollout steps
1. Add event schema for report usage and help interactions
2. Instrument wc3 report endpoints and r25 report actions
3. Build Alice hint rules from observed friction points
4. Validate improvements via reduced retries/empty-results and faster task completion

Implemented milestone (2026-03-15):
- `POST /wcapi/manage/` action `get_tally_summary_by_period` now writes an `alice_log` record (`role=user_interaction`, `name=get_tally_summary_by_period viewed`, `parent_model=report`) with filter context and result summary stats.

Implemented milestone (2026-03-15, Phase 2 start):
- Added wc3 manage actions for sales dimensions:
  - `get_tally_sales_by_customer_month`
  - `get_tally_sales_by_manufacturer_month`
  - `get_tally_sales_by_customer_year`
- Both actions aggregate Invoice totals by month and entity, return envelope-safe rows/totals, and emit `alice_log` user-interaction observations.
- Added r25 page and navigation route for phase-2 execution: `/accounts/tally-sales/list` (mode switch: monthly/yoy; dimension switch for monthly customer/manufacturer).

Implemented milestone (2026-03-15, Phase 3 start):
- Added wc3 inventory tally actions:
  - `get_tally_inventory_usage_by_month`
  - `get_tally_inventory_yearly_summary`
- Both actions aggregate `InventoryMovement` rows by item and period, include valuation using movement-layer cost with item-cost fallback, and emit `alice_log` user-interaction observations.
- Added r25 page and navigation route for phase-3 execution: `/accounts/tally-inventory/list` (mode switch: monthly/yearly).

Implemented milestone (2026-03-15, Phase 4 start):
- Added named tally execution registry service (`apps/core/services/tally_registry.py`) with canonical report keys.
- Added wc3 manage actions:
  - `get_tally_report_registry`
  - `execute_tally_report`
  - `export_tally_report`
- `export_tally_report` currently supports inline `csv` and `json` content payloads with deterministic filenames; this is the first replacement step for WC2 RecordsToText-style flows.
- Added r25 phase-4 UI and navigation route: `/accounts/tally-registry/list` with report registry listing, execute-by-`report_key`, and inline `csv/json` export download actions.

## Risks and Mitigations
- Risk: WC2 methods include hidden side effects and lock behavior
  - Mitigation: isolate parity to data outputs, not process mechanics
- Risk: legacy tally includes implicit null/zero coercions
  - Mitigation: codify numeric normalization in utility layer and tests
- Risk: report drift across periods due to timezone/date boundary rules
  - Mitigation: explicit UTC/local boundary policy in service contracts

## Validation Plan
- Build a parity harness that compares WC2 sample exports with wc3 results
- Validate by tally family before broad rollout
- Add regression tests on each migrated family to prevent drift

## Suggested Initial Implementation Backlog
1. Add accounts/services/receivable_aging_parity.py
2. Add core/services/summary_by_period.py
3. Add wcapi manage actions for both services
4. Add tests with fixture matrix for month/quarter/year ranges
5. Add report endpoint docs under readmes/topics/reports/

## Related TODO
- See [todo.md](todo.md) for the active WC2 mining backlog (layouts, methods, and migration candidates).
