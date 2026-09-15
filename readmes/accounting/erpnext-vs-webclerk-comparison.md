# ERPNext vs WebClerk — Feature Comparison

**Date:** 2026-09-08
**Purpose:** Benchmark WebClerk against ERPNext (the strongest open-source ERP) to understand where WC3 stands. ERPNext is NOT a candidate for integration — it's another ERP, which is what WebClerk already is. This comparison validates WC3's completeness and identifies genuine gaps.

---

## Why Compare?

ERPNext is the open-source benchmark. If WebClerk matches or beats ERPNext in operations, and ERPNext's advantages are all in accounting/HR territory that WC3 intentionally delegates, then the Divided architecture is validated: WC3 + a thin accounting system covers the full enterprise without either system overreaching.

---

## Comparison by Functional Area

### Legend
- **WC3 ✓** = WebClerk built and operational
- **WC3 ≈** = WebClerk partial or designed differently
- **WC3 ✗** = Not in WebClerk (may be intentional)
- **ERPNext ✓** = ERPNext built and operational
- **Divided** = WC3 intentionally delegates this to accounting software

---

### 1. Accounting & Finance

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Chart of Accounts | ✓ | ✓ | `GlAccount` model with division codes |
| Journal Entries (double-entry) | ✓ | ✓ | `GlJournal` with batch grouping, locking |
| Accounts Receivable | ✓ | ✓ | WC3 owns full AR cycle: aging → collections → payment → GL |
| Accounts Payable | ✓ | **Divided** | WC3 generates AP vouchers; accounting system manages payments |
| Bank Reconciliation | ✓ | **Divided** | Accounting system territory |
| P&L / Income Statement | ✓ | **Divided** | By design — accountant's job |
| Balance Sheet | ✓ | **Divided** | By design — accountant's job |
| Cash Flow Statement | ✓ | **Divided** | By design — accountant's job |
| Trial Balance | ✓ | ✓ | `account_summary_by_period` + `export_journals` |
| Multi-currency / FX | ✓ | ✓ | `Currency` model, `exchange_rates.py`, FX gain/loss settlement |
| Tax management | ✓ | ✓ | `TaxJurisdiction`, `tax_lookup.py`, Avalara/TaxJar ready |
| Revenue recognition | ✓ | ✓ | Deferred invoices, date-gated journalization, consignment |
| Fixed assets / depreciation | ✓ | **Divided** | Accounting system territory |
| Budgeting | ✓ | **Divided** | WC3 does "Wild Guess" from transactions; formal budgets are accounting |
| Period close | ✓ | ✓ | `eom.py` with GL balance verification |
| Cost centers | ✓ | ✓ | Division codes on GL accounts and journal lines |

**Score: ERPNext 16/16, WebClerk 9 built + 6 Divided + 1 Wild Guess = 16/16 covered**

WC3 matches ERPNext on everything operational. The 6 "Divided" features are accounting administration — exactly what a downstream accounting system handles. No gap.

---

### 2. Sales & CRM

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Customer management | ✓ | ✓ | `Customer` + `Contact` with roles |
| Leads / opportunities | ✓ | ✓ | Touch + Health metric. WC3 disqualifies (80% never buy) vs. ERPNext nurtures |
| Quotations / proposals | ✓ | ✓ | `Proposal` with expiry + follow-up |
| Sales orders | ✓ | ✓ | `Order` model with backorder via Actions |
| Invoicing | ✓ | ✓ | Full invoicing with partial/progress billing |
| Credit memos / returns | ✓ | ✓ | Negative invoice → GL adjustment |
| Customer pricing / price lists | ✓ | ✓ | `Catalog` with customer-specific discounts |
| Commissions | ✓ | ✓ | Commission forwarding + line-level % |
| Sales pipeline | ✓ | ✓ | Touch + Action + Health. **WC3 advantage:** health derived from behavior, not rep optimism |
| Communication history | ✓ | ✓ | Touch model — channel, direction, outcome, follow-up |
| Customer portal | ✓ | ✓ | Full RBAC portal with query-filtered isolation |
| Territory management | ✓ | ✓ | Via Contact/Org geography + Catalog scoping |
| Loyalty programs | ✓ | ✗ | Not built. B2B focus — loyalty programs are B2C |
| Subscription billing | ✓ | ✗ | Not built. Medium priority for service businesses |

**Score: ERPNext 14/14, WebClerk 12/14**

WC3 matches or exceeds ERPNext in B2B sales. Missing: loyalty (B2C, not needed) and subscription billing (future). **WC3 advantage:** Alice-driven pattern recognition, health-based lead scoring, disqualification philosophy.

---

### 3. Purchasing & Procurement

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Vendor management | ✓ | ✓ | `Vendor` + shared `Contact` model |
| Purchase orders | ✓ | ✓ | `Purchase` model |
| Receiving / GRN | ✓ | ✓ | `Receipt` + `ReceiptLine`, 2-way match |
| Vendor invoicing / 3-way match | ✓ | **Divided** | PO + Receipt exists; vendor invoice matching is accounting |
| Approval workflows | ✓ | ✓ | Setting-driven `status_guard.py` with amount thresholds |
| Blanket POs | ✓ | ✓ | Action records + bundle.json |
| RFQ (Request for Quotation) | ✓ | ✗ | Not built as dedicated workflow |
| Supplier scorecard | ✓ | ≈ | Data exists (receipt performance, cost variance); no computed report yet |
| Drop-ship | ✓ | ✓ | Shipto routing logic |
| Requisitions | ✓ | ✓ | `Requisition` + `RequisitionLine` |
| Subcontracting | ✓ | ≈ | Via work orders + Actions. No dedicated subcontracting model |

**Score: ERPNext 11/11, WebClerk 8 built + 1 Divided + 2 partial = 11/11 covered**

---

### 4. Inventory & Warehouse

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Item master (multi-identifier) | ✓ | ✓ | `Item` + `ItemXRef` with UPC/MPN/EAN/GTIN |
| Multi-warehouse | ✓ | ✓ | `Warehouse` with location JSON, `InventoryLayer` per warehouse |
| Lot / serial tracking | ✓ | ✓ | `Serial` + `SerialLog` + `InventoryLayer` lot field |
| BOM (multi-level) | ✓ | ✓ | `BillOfMaterial` — recursive, effectivity dates, scrap/yield, alternates |
| Inventory valuation (FIFO/AVCO) | ✓ | ✓ | `InventoryLayer` — FIFO/AVCO. No LIFO or standard cost |
| Warehouse transfers | ✓ | ✓ | Receipt records between warehouses + `InventoryMovement` |
| Cycle counting | ✓ | ≈ | `count_snapshot` field exists. No count session workflow |
| Reorder / replenishment | ✓ | ✓ | Min/max + `inventory_velocity.py` alerts |
| Kit / assembly | ✓ | ≈ | BOM exists, kit workflow needs Flight Simulator training |
| Reservations / allocations | ✓ | ✓ | `InventoryReservation` model |
| Quality inspection | ✓ | ✓ | `qa_service.py` + QA document templates |
| Batch / expiry management | ✓ | ≈ | Lot field exists, no expiry date tracking |
| Stock reconciliation | ✓ | ≈ | Partial — count snapshot but no reconciliation workflow |

**Score: ERPNext 13/13, WebClerk 8 built + 4 partial = 12/13**

Close match. Gaps are workflow polish (cycle count sessions, expiry tracking), not missing architecture.

---

### 5. Manufacturing

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Work orders | ✓ | ✓ | `WorkOrder` + `spawn_workorder()` |
| BOM explosion / MRP | ✓ | ≈ | BOM rollup exists. No MRP scheduling engine |
| Production scheduling | ✓ | ≈ | Action/Project-based, not MRP-driven |
| Subcontracting | ✓ | ≈ | Via work orders + Actions |
| Scrap / yield tracking | ✓ | ≈ | BOM fields exist. No production actuals |
| Backflush | ✓ | ✗ | Not built |
| Process manufacturing | ✓ | ✗ | Not built (formula-based, co-products) |

**Score: ERPNext 7/7, WebClerk 1 built + 4 partial + 2 not built = 5/7**

Manufacturing is WC3's weakest area vs ERPNext. Appropriate — WC3 targets distribution-heavy SMBs with light assembly, not manufacturing-heavy operations.

---

### 6. HR & Payroll

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Employee management | ✓ | ✗ | Not WC3's domain |
| Payroll | ✓ | ✗ | Not WC3's domain |
| Leave management | ✓ | ✗ | Not WC3's domain |
| Expense claims | ✓ | ✗ | Not WC3's domain |
| Recruitment | ✓ | ✗ | Not WC3's domain |

**Score: ERPNext 5/5, WebClerk 0/5**

Intentionally out of scope. HR/payroll is a separate system. ERPNext's inclusion of HR is why it's an ERP, not an accounting system.

---

### 7. Project Management

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Projects with tasks | ✓ | ✓ | `Project` model with tasks JSON, burndown |
| Timesheets | ✓ | ✗ | Not built |
| Project billing | ✓ | ✗ | Not built |
| Gantt visualization | ✓ | ✓ | Full `UnifiedGantt.tsx` implementation |
| Resource allocation | ✓ | ✗ | Not built |

**Score: ERPNext 5/5, WebClerk 2/5**

WC3's project management is task-oriented (Actions + Projects), not resource/billing oriented. Gap acknowledged.

---

### 8. E-Commerce & Portal

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| Website / product catalog | ✓ | ≈ | Catalog exists for B2B distribution, not consumer storefront |
| Shopping cart | ✓ | ≈ | Frontend component exists, needs server-side pricing |
| Customer portal | ✓ | ✓ | Full RBAC portal |
| Vendor portal | ✓ | ✓ | `user_vendor` role with query-filtered access |
| Payment gateway | ✓ | ✓ | Spreedly (Stripe/PayPal/Braintree) |

**Score: ERPNext 5/5, WebClerk 3 built + 2 partial = 5/5 covered**

Different philosophy: WC3 is B2B commerce, not B2C storefront. Portal architecture is stronger than ERPNext's.

---

### 9. Integration & Platform

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| REST API | ✓ | ✓ | Full wcapi layer, all models |
| Webhooks | ✓ | ≈ | Connection model supports webhooks, no dispatcher |
| Import/export | ✓ | ✓ | Bundle pack/unpack, export_data, CSV |
| Multi-company | ✓ | ✓ | `Workspace` model, multi-DB config |
| Multi-currency | ✓ | ✓ | `Currency` model + exchange rates |
| Custom fields | ✓ | ✓ | JSON envelopes — infinite custom fields without schema changes |
| Workflow engine | ✓ | ✓ | `status_guard.py` — Setting-driven state machine |
| Print formats | ✓ | ✓ | SVG template workflow, WeasyPrint PDF |
| Email | ✓ | ✓ | Email model, mail merge, templates, Celery |
| Mobile access | ✓ | ≈ | React SPA works on mobile, no PWA |

**Score: ERPNext 10/10, WebClerk 8 built + 2 partial = 10/10 covered**

---

### 10. AI / Intelligence Layer

| Feature | ERPNext | WebClerk | Notes |
|---------|---------|----------|-------|
| AI agent layer | ✗ | ✓ | **Alice** — pattern recognition, coaching, margin erosion |
| Transaction pattern recognition | ✗ | ✓ | observe → log → pattern → recommend → promote |
| Freight cost calibration | ✗ | ✓ | Alice reconciles estimated vs actual nightly |
| Data conversion intelligence | ✗ | ✓ | Claude Haiku column mapping, multi-pass |
| Onboarding / flight simulators | ✗ | ≈ | Architecture decided, not fully built |
| Customer quality feedback | ✗ | ≈ | Small-Stings designed |

**Score: ERPNext 0/6, WebClerk 4 built + 2 designed = 6/6**

**This is WC3's decisive advantage.** ERPNext has no equivalent. Alice as an embedded AI agent is a category difference, not a feature difference.

---

## Summary Scorecard

| Category | ERPNext | WebClerk Built | WC3 Partial/Divided | WC3 Total | Notes |
|----------|---------|----------------|---------------------|-----------|-------|
| Accounting & Finance | 16 | 9 | 7 (Divided) | 16 | Divided by design |
| Sales & CRM | 14 | 12 | 0 | 12 | Missing: loyalty, subscriptions |
| Purchasing | 11 | 8 | 3 | 11 | Close match |
| Inventory | 13 | 8 | 4 | 12 | Workflow polish gaps |
| Manufacturing | 7 | 1 | 4+2 | 5 | WC3 weakest area — by design |
| HR & Payroll | 5 | 0 | 0 | 0 | Out of scope |
| Projects | 5 | 2 | 0 | 2 | Time/billing gap |
| E-Commerce | 5 | 3 | 2 | 5 | B2B vs B2C difference |
| Integration | 10 | 8 | 2 | 10 | Close match |
| AI Layer | 0 | 4 | 2 | 6 | **WC3 advantage** |
| **Totals** | **86** | **55** | **26** | **79** | **92% coverage** |

---

## Key Findings

### 1. WebClerk matches or beats ERPNext in operations
Sales, CRM, purchasing, inventory, fulfillment, integration — WC3 is competitive or superior in every operational area. The Touch/Health/Alice combination for CRM is genuinely better than ERPNext's traditional lead pipeline.

### 2. ERPNext's advantages are all in accounting/HR
The features WC3 lacks (AP management, financial statements, HR, payroll, MRP) are exactly the features a downstream accounting system provides. The Divided architecture is validated — WC3 + LedgerSMB (or similar) covers the full enterprise.

### 3. WC3's AI layer is a category advantage
ERPNext has no Alice. No pattern recognition. No embedded coaching. No margin erosion detection. No Small-Stings. This is not a feature gap ERPNext can close with a plugin — it's an architectural difference.

### 4. ERPNext is the wrong integration choice
ERPNext duplicates everything WC3 already does well (sales, purchasing, inventory) and adds accounting/HR that WC3 intentionally doesn't do. Integrating ERPNext means maintaining business logic in two systems — the exact problem the Divided philosophy avoids. A thin accounting system (LedgerSMB, Akaunting, GnuCash) that accepts GL journals is the right complement.

### 5. WC3's JSON envelope architecture is underappreciated
ERPNext uses custom fields (DocType-based). WC3 uses JSON envelopes (PJPV). WC3's approach is more flexible — infinite custom fields without schema migrations, one compute engine, one source of truth. This is a structural advantage that compounds over time.

---

## What This Means for the Accounting Integration

**Don't add ERPNext.** Add a thin accounting system that:
1. Accepts balanced GL journal entries from WC3
2. Accepts AP vouchers with vendor/invoice/terms detail
3. Manages AP payments, bank reconciliation, financial statements
4. Exposes an API for chart of accounts sync and trial balance query

LedgerSMB fits this description. So does Akaunting. So does GnuCash for simple installations. The AccountingAdapter pattern makes the choice reversible.
