# GL & Accounting — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 GL_* mining (36 methods → 8 WC3 functions)

---

## Principle

WebClerk is commerce, not accounting. WC3 produces GL journal entries. Accounting programs consume them. We never build P&L, Balance Sheet, or trial balance.

---

## Journal Types

| Type | Source | Debit | Credit |
|---|---|---|---|
| **Sales** | Invoice | AR | Revenue + COGS/Inventory |
| **Cash** | Payment | Cash | AR |
| **Purchase** | Purchase receipt | Inventory | AP |
| **BOM** | Assembly build | Finished goods inventory | Component inventory |
| **Adjustment** | Count variance, scrap | Inventory or COGS | COGS or Inventory |

All five flow through `journalize.py`. One file, no redundancy (WC2 had 36 methods).

---

## GlJournal Model

```
GlJournal
  ├── account              → GL account code
  ├── debit / credit       → one is set, other is null
  ├── source               → 'automation' | 'manual'
  ├── type                 → 'sales' | 'general' | 'purchase' | 'bom' | 'adjustment'
  ├── source_id            → FK to originating record (invoice, payment, etc.)
  ├── source_model         → 'invoice' | 'payment' | 'purchase' | 'bom_build' | 'adjustment'
  ├── division             → department/division code
  ├── batch_id             → groups lines into one posting batch
  ├── date_posted          → accounting date (may differ from dt_created)
  ├── is_posted            → true after exported to accounting package
  └── note                 → description
```

---

## Core Functions

| Function | What It Does |
|---|---|
| `journalize_invoice(id)` | AR + Revenue + COGS + Inventory per line, with commission |
| `journalize_payment(id)` | Cash + AR |
| `journalize_purchase(id)` | Inventory + AP per line |
| `journalize_bom_build(batch_id, parent, qty, components)` | FG inventory + component inventory transfer |
| `journalize_adjustment(item_id, qty, cost, reason)` | Inventory ↔ COGS (positive = found, negative = lost/scrapped) |
| `batch_journalize()` | All un-journalized documents in one pass |
| `account_summary_by_period(year, month)` | $ by account code — the screen users retype |
| `export_journals(year, month, format)` | CSV / JSON / Tab / QuickBooks IIF |
| `tax_summary_by_period(year, month, months)` | Tax collected by jurisdiction for filing |
| `mark_period_reconciled(year, month)` | User confirms GL export matches accounting package |
| `reverse_gl_entries(instance)` | Void — creates contra entries (debit↔credit swap) |

---

## Account Mapping (4-level lookup)

```
1. Item.gls (per-item: revenue, cogs, inventory accounts)
2. Customer/Org override (customer-specific revenue or AR account)
3. TaxJurisdiction (tax payable account)
4. DEFAULTS fallback (ASSET-AR-000, REV-SALES-000, etc.)
```

---

## Ledger System (AR/AP Aging)

```
Ledger (one per invoice installment period + one per payment)
  ├── value_original       → immutable initial amount
  ├── value_available      → current unpaid balance (decreases with payments)
  ├── dt_due               → when payment is owed — drives aging
  ├── dt_discount_due      → when early-pay discount expires
  ├── discount_potential   → discount rate (e.g., 0.02 = 2%)
  ├── org FK               → customer/vendor for indexed queries
  ├── invoice FK           → which invoice
  ├── term FK              → payment terms
  ├── is_settled           → true when fully paid
```

Invoice ledgers: positive. Payment ledgers: negative. Sum = current balance.

Multi-period installments: one invoice → N ledger records, each aging independently. Terms like "3-Pay Net 90" create 3 records with staggered due dates.

---

## Aging Buckets

```
Future:    due > today + 30
Current:   today < due ≤ today + 30
Period 1:  0-30 days past due
Period 2:  31-60 days past due
Period 3:  60+ days past due
```

Live query — no batch calculation needed.

---

## Credit Decision Metrics (on org.financial)

| Metric | What It Is |
|---|---|
| `days_avg_paid` | Mean days from due to settled on closed invoices |
| `high_credit` | Peak balance ever reached |
| `open_orders` | Sum of unfilled order backlog |
| `total_exposure` | AR + open orders |

---

## EOM Close (533 lines)

`run_eom_close(year, month)` — idempotent, re-runnable:
1. Aging recalculation
2. GL balance verification (debits = credits)
3. Period summary generation
4. Transaction locking (journalized docs become read-only)
5. Audit trail

`reopen_period()` unlocks if correction needed.

---

## Export Formats

| Format | Use Case |
|---|---|
| CSV | Bookkeeper opens in Excel, copy-pastes into QuickBooks |
| JSON | API integration or archive |
| Tab | Tab-delimited for older systems |
| QuickBooks IIF | Direct import into QuickBooks Desktop |

Most users read the account summary screen and retype. The export is for the bookkeeper.

---

## Commerce Dashboard — Accounting Tab

Shows: AR aging buckets, credit metrics, document counts for period, unaccounted prior period (clickable → DataBrowser), $ by account code table, export buttons, reconciliation status.

---

## Company Profile (Setting #438)

Company name, address, phone, EIN, logo paths, print defaults, accounting interface config (package, format, fiscal year). Used for letterhead on all printed reports.

---

## Files

| File | Purpose |
|------|---------|
| `apps/accounts/services/journalize.py` | All journal functions + export + tax summary + reconciliation |
| `apps/accounts/services/eom.py` | EOM close, reopen, status |
| `apps/accounts/services/ledger_balance.py` | Aging, balances, credit metrics, reconcile, rebuild |
| `apps/accounts/services/terms_ledger.py` | Payment schedule → ledger records |
| `apps/accounts/services/gl_defaults.py` | Account mapping defaults |
| `apps/accounts/models/gl_account.py` | Chart of accounts |
| `apps/accounts/models/gl_journal.py` | Journal entries |
| `apps/accounts/models/ledger.py` | AR/AP aging tracker |
| `apps/core/management/commands/seed_company_settings.py` | Company profile |
