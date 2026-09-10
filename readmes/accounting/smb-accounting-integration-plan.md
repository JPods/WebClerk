# SMB Accounting Integration Plan for WebClerk

**Date:** 2026-09-08
**Status:** Draft — ready for evaluation
**Source:** gl_interface.md (junkdrawer) + SMB Enterprise Feature Comparison

---

## The Principle

WebClerk runs the company. The accounting system keeps the books.

WC3 is a commerce engine — it sells, purchases, ships, manufactures, and collects. It produces clean, balanced GL journal entries and AP vouchers. An accounting system consumes those entries and handles everything downstream: financial statements, AP payments, bank reconciliation, tax filing, period close.

This is the **Divided** philosophy applied to software: each system does what it's good at. WC3 never builds P&L, Balance Sheet, Trial Balance, or Cash Flow. The accounting system never manages inventory, sales orders, or CRM.

---

## The Boundary

```
                 WEBCLERK (operations)
 ┌─────────────────────────────────────────┐
 │ CRM / Touches / Health scoring          │
 │ Proposals → Orders → Invoices           │
 │ Purchase Orders → Receipts              │
 │ Work Orders / BOM / QA                  │
 │ Inventory (FIFO layers, reservations)   │
 │ Shipping (pick/pack/ship)               │
 │ AR: billing → aging → collections       │
 │ GL Journal generation (double-entry)    │
 │ Alice: pattern recognition, coaching    │
 └───────────────────┬─────────────────────┘
                     │
              Two interfaces:
              ┌──────▼──────┐
              │ GL Journals │  ← revenue, COGS, inventory,
              │             │    accruals, adjustments
              │ AP Vouchers │  ← vendor + invoice + due date
              │             │    + amount + GL distribution
              └──────┬──────┘
                     │ API or file export
                     ▼
              ACCOUNTING SYSTEM
 ┌─────────────────────────────────────────┐
 │ General Ledger                          │
 │ Accounts Payable (aging, payments)      │
 │ Cash / Checkbooks                       │
 │ Bank Reconciliation                     │
 │ Trial Balance                           │
 │ P&L / Income Statement                  │
 │ Balance Sheet                           │
 │ Cash Flow Statement                     │
 │ Tax filing support                      │
 │ Period close                            │
 └─────────────────────────────────────────┘
```

---

## What WC3 Already Has

From the SMB Enterprise Feature Comparison (116 features, 75%+ coverage):

### GL Infrastructure (Built)
- `GlAccount` model — chart of accounts with division codes
- `GlJournal` — double-entry journal lines with batch grouping and locking
- `account_summary_by_period` — trial balance data
- `export_journals` — journal export
- `eom.py` — period close with GL balance verification
- `journalize_purchase()` — purchase-to-GL pipeline

### AR Cycle (Built — WC3 owns this entirely)
- `aged_receivables.py` — full aging (future/current/30/60/90)
- `collections_dashboard.py` — DSO, top past-due, payment velocity, health scoring
- Customer statements via `statement_views.py`
- Finance charge calculation
- Credit management (`check_credit_limit`, credit hold logic)
- Payment processing via Spreedly (Stripe/PayPal/Braintree)

### Tax (Built)
- `TaxJurisdiction` model with sales/cost/shipping rates
- `tax_lookup.py` — rate resolution
- Avalara/TaxJar field for complex jurisdictions

### What WC3 Intentionally Does NOT Have
- AP aging or vendor payment scheduling → accounting system
- Bank reconciliation → accounting system
- Financial statements (P&L, BS, CF) → accounting system
- Fixed asset management → accounting system
- Budgeting/forecasting → spreadsheets or accounting system
- Vendor invoice 3-way match → accounting system
- Labor/payroll → separate system entirely

---

## The AccountingAdapter Interface

System-independent abstraction — WebClerk customers choose their accounting system.

```python
class AccountingAdapter:
    """Base interface for all accounting system integrations."""

    # --- Outbound (WC3 → Accounting) ---
    def post_journal(self, journal_batch):
        """Post balanced GL journal entries."""

    def post_vendor_invoice(self, vendor, invoice_number, due_date,
                            amount, gl_distribution, wc_uuid):
        """Post AP voucher with full vendor detail."""

    def post_vendor_credit(self, vendor, credit_memo, amount, wc_uuid):
        """Post vendor credit memo."""

    # --- Inbound (Accounting → WC3) ---
    def get_chart_of_accounts(self):
        """Sync chart of accounts for GL code validation."""

    def get_vendor_balance(self, vendor_id):
        """Query outstanding AP for a vendor."""

    def get_trial_balance(self, as_of_date):
        """Pull trial balance for dashboard display."""

    # --- Sync ---
    def sync_payments(self, since_date):
        """Pull vendor payments posted in accounting system
        to update WC3 purchase status."""
```

Implementations:
```
LedgerSMBAdapter    ← PostgreSQL-native, API
AkauntingAdapter    ← REST API (Laravel)
GnuCashAdapter      ← file-based (XML/SQLite)
QuickBooksAdapter   ← OAuth2 REST API
XeroAdapter         ← OAuth2 REST API
GenericCSVAdapter   ← flat file export/import (fallback)
```

---

## Journal Batch Format

WC3's GL export must be clean, complete, and importable by any system.

```json
{
  "batch_id": "WC-2026-09-08-001",
  "company": "Acme Distribution",
  "generated_at": "2026-09-08T14:30:00Z",
  "source": "webclerk",
  "entries": [
    {
      "date": "2026-09-08",
      "reference": "INV-4821",
      "wc_uuid": "a1b2c3d4-...",
      "description": "Sale to ABC Motors",
      "lines": [
        {"account": "1200", "debit": 8500.00, "credit": 0, "party": "ABC Motors", "cost_center": "East"},
        {"account": "4000", "debit": 0, "credit": 7500.00, "party": null, "cost_center": "East"},
        {"account": "2300", "debit": 0, "credit": 680.00, "party": null, "cost_center": null},
        {"account": "5000", "debit": 0, "credit": 320.00, "party": null, "cost_center": null}
      ]
    }
  ],
  "control_totals": {
    "entry_count": 1,
    "total_debits": 8500.00,
    "total_credits": 8500.00,
    "balanced": true
  }
}
```

---

## AP Voucher Format

Separate from GL because the accounting system needs vendor/invoice detail for AP management.

```json
{
  "voucher_id": "WC-AP-2026-09-08-001",
  "vendor": {
    "name": "ABC Motors",
    "wc_vendor_id": 1247,
    "tax_id": "12-3456789"
  },
  "invoice_number": "92715",
  "invoice_date": "2026-09-08",
  "due_date": "2026-10-15",
  "terms": "Net 30",
  "wc_purchase_uuid": "e5f6g7h8-...",
  "gl_distribution": [
    {"account": "1400", "amount": 8000.00, "description": "Inventory — brake assemblies"},
    {"account": "5200", "amount": 500.00, "description": "Freight in"}
  ],
  "total": 8500.00
}
```

---

## Candidate Accounting Systems (Ranked)

ERPNext is excluded — it's another ERP, which is what WebClerk already is.

### 1. LedgerSMB — Recommended First Evaluation

**Why:** Accounting-first, not ERP-first. PostgreSQL-native (same as WC3). Open source (GPL v2). "WebClerk runs the company; LedgerSMB keeps the books."

- Full double-entry GL, AP, AR (AR overlap — WC3 owns AR operationally, LedgerSMB gets the journal)
- Bank reconciliation
- Financial statements (P&L, BS, TB)
- Multi-currency
- PostgreSQL — could share the same server, different databases
- Perl/JS stack — different from WC3's Python/React but doesn't matter for API integration

**Evaluate:** API quality for journal import, vendor invoice import. Can WC3 post programmatically?

### 2. Akaunting — Second Evaluation

**Why:** Modern web UI (Laravel/Vue), REST API, lightweight. Closer to "thin accounting layer."

- Double-entry, chart of accounts, manual journals
- GL, BS, TB reports
- Bank reconciliation
- REST API for programmatic posting

**Concern:** BSL license (not truly open source). Paid modules may be needed. Evaluate licensing carefully before committing.

### 3. GnuCash — For Simple/Local Installations

**Why:** Free, genuine double-entry, AP/AR, business reports. Perfect for single-user desktop installations (matches WC3's desktop hosting lineage).

- Full GL, AP, AR, financial statements
- Vendor reports, AP aging
- SQLite or XML backend

**Weakness:** No multi-user web architecture. Integration is file-based (import/export), not API. Best for small operations where one person does both commerce and books.

### 4. QuickBooks/Xero — For Customers Who Already Use Them

**Why:** Market reality. Many SMBs already have QuickBooks or Xero. WC3 should be able to export to them.

- Both have OAuth2 REST APIs
- Journal entry import is well-documented
- Vendor bill import is well-documented

**Build:** `QuickBooksAdapter` and `XeroAdapter` as second-phase implementations after the core adapter pattern is proven with LedgerSMB or Akaunting.

---

## Implementation Phases

### Phase 1: GL Export (build now)
- `GenericCSVAdapter` — export GL journals in standard CSV format
- `GenericJSONAdapter` — export in the JSON batch format above
- Management command: `python manage.py export_gl --from 2026-09-01 --to 2026-09-30`
- This works with ANY accounting system that can import journals

### Phase 2: LedgerSMB Integration (evaluate + build)
- Install LedgerSMB locally
- Map WC3 chart of accounts → LedgerSMB chart of accounts
- Build `LedgerSMBAdapter` — programmatic journal + AP voucher posting
- Test round-trip: WC3 sale → GL journal → LedgerSMB → financial statements

### Phase 3: Additional Adapters
- `QuickBooksAdapter` — for customers who use QBO
- `XeroAdapter` — for customers who use Xero
- `AkauntingAdapter` — if licensing checks out

### Phase 4: Bi-directional Sync
- Pull chart of accounts from accounting system → validate WC3 GL codes
- Pull vendor payment status → update WC3 purchase records
- Pull trial balance → display on WC3 dashboard

---

## Design Rules

1. **WC3 journals must always balance.** Control totals on every batch. Reject before export if debits ≠ credits.
2. **WC3 UUID on every entry.** The accounting system stores WC3's UUID so entries can be traced back to source transactions.
3. **AP vouchers are separate from GL journals.** GL journals move numbers. AP vouchers move numbers + vendor identity + payment terms. The accounting system needs both.
4. **No accounting logic in WC3.** WC3 never calculates depreciation, amortization, period-end adjustments, or financial ratios. Those are the accountant's job.
5. **The adapter is the only boundary.** All accounting system communication goes through the adapter. No direct database writes, no bypassing the interface.
6. **GenericCSV is always available.** Even if no adapter is configured, WC3 can always export flat files. No customer is locked out of accounting integration.
