# Go-Live Todo — WebClerk 3.0

Rebuilt 2026-08-06 with per-item status and priority. Prior version archived at `_archive/todo-go-live-2026-08-05.md`.
Alice pointer: Document `wc3-go-live` (id: 945).

**Statuses:** DONE | READY | BLOCKED | TODO | DEFERRED

**Priorities:**
- **P1** — Must have for ramp-up. Orgs, transactions, items, serials, BOM, structural decisions that get messy later.
- **P2** — Important for daily use. Reports, workflows, guard rails that prevent bad data.
- **P3** — Nice to have. Efficiency, polish, power-user features.
- **P4** — Can wait months. Analytics, tallies, trend reporting. No harm deferring.

## Summary

| | Count |
|---|---|
| Total items | 108 |
| DONE | 60 |
| BLOCKED | 0 |
| TODO | 47 |
| DEFERRED | 1 |
| READY | 1 |
| **Progress** | **56%** |

| Priority | Remaining |
|----------|-----------|
| P1 | 11 |
| P2 | 16 |
| P3 | 14 |
| P4 | 6 |

---

### Go-Live Gate

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 1 | Customer can pay (Spreedly hosted fields) | DONE | P1 | SpreedlyCardForm.tsx wired into PaymentDialog 2026-08-06. Manual + Card modes. Gateway config endpoint added. |
| 2 | Proposal → Order → Invoice chain | DONE | — | ManageActionPanel wired into TransactionDetail 2026-08-06. |
| 3 | Tax calculates | DONE | — | Built-in US sales tax. Per-line override. Jurisdiction seed. |
| 4 | Inventory adjusts on ship | DONE | — | Pending path, lock lifecycle, layer accounting. |
| 5 | User can print invoice | DONE | — | Universal print renderer, 7 layouts, Cmd+P. |
| 6 | Shipping recorded | DONE | — | Manual entry in PackingPanel. Carrier APIs built, UI not wired. |
| 7 | Commission calculates | DONE | — | Auto-populate, per-line, staff-only. |
| 8 | Internal data protected | DONE | — | Commission, gateway, cost fields stripped for non-staff. |

### Security

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 9 | Gateway sanitization | DONE | — | |
| 10 | Rate limiting | DONE | — | |
| 11 | Field-level RBAC | DONE | — | |
| 12 | Commission stripping (non-staff) | DONE | — | |
| 13 | `_STAFF_ONLY_ACTIONS` | DONE | — | |
| 14 | Inventory lock lifecycle | DONE | — | |
| 15 | `is_staff`/`is_superuser` on auth | DONE | — | |
| 16 | C toggle/totals/panels gated | DONE | — | |

### Bug Fixes

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 17 | po_totals import | DONE | — | |
| 18 | Payment race condition | DONE | — | |
| 19 | Orphan locks | DONE | — | |
| 20 | CASCADE verified | DONE | — | |
| 21 | Multi-currency skeleton | DONE | — | |

### Inventory

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 22 | `inventory_pending.py` (acquire/release lock, clear stale) | DONE | — | |
| 23 | `InventoryAdjust.tsx` | DONE | — | |
| 24 | `CycleCountMobile.tsx` | DONE | — | |
| 25 | `InventoryLayersPanel` | DONE | — | |

### Tax

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 26 | `totals.py` per-line calc, exemption, audit trail | DONE | — | |
| 27 | Jurisdiction seed | DONE | — | |
| 28 | Line_type toggles, tax% column | DONE | — | |
| 29 | `TaxReportPrintDocument` | DONE | — | |
| 30 | Avalara / TaxJar integration | DEFERRED | P3 | Connection records ready. ~1 session each. |

### Packing & Shipping

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 31 | `generate_pick_list`, `confirm_pack`, `ship_order` | DONE | — | |
| 32 | `PackingPanel.tsx` (3-step: pick/pack/ship) | DONE | — | |
| 33 | Partial shipment | DONE | — | |
| 34 | `CarrierBase` + UPS/FedEx/USPS/DHL (4 carriers) | DONE | — | Backend only. |
| 35 | Rate shopping panel | TODO | P3 | ~1 session. |
| 36 | Label display/print | TODO | P3 | ~1 session (combine with #35). |
| 37 | Tracking status panel | TODO | P3 | ~1 session (combine with #35). |
| 38 | Address validation | TODO | P3 | ~1 session. |

### Printing & Reports

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 39 | `seed_print_layouts` (7 models) | DONE | — | |
| 40 | 13 print documents, `UniversalPrint.ts` | DONE | — | |
| 41 | ReportsDialog, Cmd+P, `DetailToolbar` | DONE | — | |
| 42 | Alice drafts layouts from PDF/image | DONE | — | |
| 43 | Batch printing (select multiple, combined PDF) | TODO | P3 | ~1 session. |
| 44 | Scheduled reports (Celery) | TODO | P3 | ~1 session. |
| 45 | Statement generation (customer, date range) | TODO | P2 | ~1 session. Need for AR follow-up. |
| 46 | Aged receivables report (30/60/90/120+) | TODO | P2 | ~1 session. Need for AR follow-up. |
| 47 | Inventory valuation report (FIFO/LIFO) | TODO | P3 | ~1 session. |

### Payment

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 48 | `SpreedlyService` (purchase/authorize/capture/void/credit/refund) | DONE | — | Backend. |
| 49 | `process_payment`/`refund_payment` | DONE | — | Backend. |
| 50 | Webhook endpoint | DONE | — | Backend. |
| 51 | Gateway Setting, response sanitization | DONE | — | Backend. |
| 52 | Spreedly hosted fields iframe | DONE | P1 | SpreedlyCardForm.tsx — iframes for card number + CVV. Token-in-a-token. 2026-08-06. |
| 53 | Apple Pay / Google Pay | TODO | P3 | ~1 session after #52. |
| 54 | 3D Secure | TODO | P3 | ~1 session after #52. |
| 55 | Refund button | TODO | P2 | Needed once payments are live. |
| 56 | Saved cards (tokenized) | TODO | P3 | |

### TechNotes & Templates

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 57 | `MarkdownEditor` | DONE | — | |
| 58 | `{{token}}` syntax, template seed | DONE | — | |
| 59 | Field path endpoint (`/wcapi/model_name/field_paths/`) | TODO | P3 | Token picker auto-discovery. ~1 session. |
| 60 | Email merge (token engine renders email body) | TODO | P2 | ~1 session. Needed for customer communication. |
| 61 | Save user templates as Setting records | TODO | P3 | ~1 session. |

### Serial Tracker

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 62 | 9 statuses, lifecycle methods, SerialLog | DONE | — | |
| 63 | Setting #545, Pydantic schema | DONE | — | |
| 64 | SerialCard, SerialDetailCard, SerialSelectPanel, SerialPanel | DONE | — | |

### Schema Infrastructure

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 65 | 79 schema_map Settings | DONE | — | |
| 66 | 73 Pydantic schemas | DONE | — | |
| 67 | `seed_all_schema_maps` | DONE | — | |
| 68 | Alice schema question log + weekly review actions | DONE | — | |

### Conversion Chain

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 69 | `conversion.py` | DONE | — | Backend. |
| 70 | `proposal_to_order.py` | DONE | — | Backend. |
| 71 | `order_to_invoice.py` | DONE | — | Backend. |
| 72 | `ManageActionPanel.tsx` (all buttons wired) | DONE | — | Component exists. |
| 73 | ManageActionPanel rendered in TransactionDetail | DONE | — | Wired 2026-08-06. Import + render after sections. |

### Commission

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 74 | Auto-populate, per-line, staff-only | DONE | — | |
| 75 | Reports on rep/employee models | DONE | — | |
| 76 | Commission panel (rep summary cards, per-line table) | TODO | P2 | `CommissionPanel.tsx` exists. ~1 session. |
| 77 | Commission script basis (execute stored scripts) | TODO | P3 | ~1 session. |
| 78 | Commission payment (pay accrued, create payment records) | TODO | P2 | ~1 session. |

### Detail Pages

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 79 | Item detail enrichment (sales history, margins, images) | TODO | P1 | Items are core. Summary tab is thin. ~1-2 sessions. |
| 80 | Requisition detail page | READY | P3 | DataBrowser covers it. ~1 session if custom needed. |
| 81 | Work Order detail page (BOM explosion, labor) | TODO | P1 | BOM is core relationship structure. ~1 session. |
| 82 | Receipt detail page (receive vs PO, inspect, put-away) | TODO | P1 | Receive against PO is core transaction flow. ~1 session. |

### Commerce Features

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 83 | BOM editor (edit mode for BomPanel) | DONE | P1 | Full edit: add component search, qty/scrap/sequence/optional/alternate/dates/revision. 2026-08-06. |
| 84 | Variant manager (parent + grid, variant-level pricing) | TODO | P5 | Item structure — must be right before data accumulates. ~1 session. |
| 85 | Catalog / price list editor (tiers, dates, volume breaks) | TODO | P5 | Pricing structure — hard to retrofit. ~1 session. |
| 86 | Warehouse management (locations, bins, transfers) | TODO | P5 | Structural — inventory locations must exist before stock moves. ~1 session. |
| 87 | Status guard rails (no invoice without order, etc.) | TODO | P2 | Prevents bad data. Another session is working on this. ~1 session. |
| 88 | Approval workflows (Draft → Submitted → Approved) | TODO | P5 | Uses Action records. ~1 session. |
| 89 | Return / credit memo (from invoice, reverse inventory) | TODO | P1 | Core transaction type. Structural — needs its own flow. ~1 session. |
| 90 | Cancellation workflow (reason, reverse reservations) | TODO | P2 | ~1 session. |
| 91 | Document cloning (copy transaction for repeat order) | TODO | P2 | ~1 session. |
| 92 | Batch status update (multi-select, bulk change) | TODO | P3 | ~1 session. |
| 93 | Visual flow indicator (Proposal → Order → Invoice → Payment) | DONE | — | TransactionFlowIndicator.tsx wired 2026-08-06. |
| 94 | Discount / promotion engine (coupons, volume, customer rules) | TODO | P2 | ~1-2 sessions. |

### Cross-System

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 95 | PO → SO bundle (field mapping, conversion, status dashboard) | TODO | P1 | Structural — defines how purchase and sales sides connect. ~2 sessions. |

### Analytics & Reporting (salvaged from WC2 Tally system)

| # | Item | Status | Pri | Notes |
|---|------|--------|-----|-------|
| 96 | Monthly usage rollup (sales qty, orders, purchases, adjustments, scrap by item by month) | TODO | P4 | Foundation for turns, reorder, margin velocity. WC2: `Tally_dInvent.4dm`, `TallyMonthlyUsage.4dm`, `TallyYearlyUsageSum.4dm`. ~1-2 sessions. |
| 97 | Inventory turns + margin factor (cost/inventory×12, weighted avg cost) | TODO | P4 | Depends on #96 + #47. WC2: `TallyEOMInvento.4dm`, `TallyInventoryValue.4dm`, `TallyInventoryProcess.4dm`. ~1 session. |
| 98 | Sales by customer × month with margin% | TODO | P4 | WC2: `TallyCustSaleMo.4dm`, `TallySalesMonth2Date.4dm`, `TallySalesByCustomerByMonth.4dm`. ~1 session. |
| 99 | Sales by vendor × month | TODO | P4 | WC2: `TallyVendSaleMo.4dm`, `TallySalesByMfrByMonth.4dm`. ~1 session. |
| 100 | Quarterly sales by rep with COGS + margin | TODO | P4 | WC2: `Tally_SaleIDQtr.4dm`. ~1 session. |
| 101 | Open order amounts by customer | TODO | P2 | Useful during ramp-up for AR visibility. WC2: `Tally_OpenOrdAm.4dm`. ~1 session. |
| 102 | Available qty by item (on hand − on order − allocated) | TODO | P2 | Real available-to-promise. Needed once orders flow. WC2: `Tally_OpenItmAm.4dm`. ~1 session. |
| 103 | Ad source / campaign ROI (cost per response, pace items, 1st order value) | TODO | P4 | WC2: `Tally_AdLeads.4dm`, `Tally_AdSales.4dm`. ~1 session. |
| 104 | Period summary report (invoices+orders+proposals+POs+customers+leads by date range by rep) | TODO | P3 | Extends `get_dashboard_counts`. WC2: `TallySummaryByPeriod.4dm`. ~1 session. |
| 105 | Sales by customer × year (multi-year trend) | TODO | P4 | WC2: `TallySalesByYearByCustomer.4dm`. ~1 session. |
| 106 | Work order cost rollup (labor time × rate + materials by activity) | TODO | P3 | WC2: `Tally_OrdProfit.4dm`. ~1 session. |
| 107 | EOM inventory snapshot (qty on hand, value, type by item) | TODO | P4 | WC2: `TallyUsageEOMValue.4dm`. ~1 session. |
| 108 | Sales history into customer record (YTD, last year, lifetime) | TODO | P2 | Denormalized for fast org lookup. WC2: `TallySalesIntoCustomerRecord.4dm`, `TallyEndOfYr.4dm`. ~1 session. |

---

## Architecture Notes (from Phase 1 build — 2026-08-05)

**Pending is the write path for inventory and cash.** No direct mutations. Every inventory change and every payment application creates a PendingInventoryAdjustment or PendingPaymentApplication first, then applies immediately if the target is unlocked. One path, one audit trail.

**Lock lifecycle is complete.** `acquire_lock()` → `release_lock()` → pending drains. `check_lock_expired()` auto-clears after 5 minutes. `clear_stale_locks` management command for orphan recovery.

**Bulk import uses the established pipeline.** External data → JSON (Alice/Athena) → Bundle record import. No CSV upload features.

**Approval workflow uses Action records.** No custom approval system. Adjustments over threshold create an Action directed to the Responsible Person.

**Commission is internal-only.** Staff-only gates at every layer.

**Carrier abstraction.** `CarrierBase` with `@register_carrier` decorator. 4 carriers: UPS, FedEx, USPS, DHL.

---

*Prior version: `_archive/todo-go-live-2026-08-05.md`*
