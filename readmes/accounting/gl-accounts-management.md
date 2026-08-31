# GL Accounts Management (wc3)

## Purpose
This document defines how WebClerk3 assigns and stages GL accounts for org roles, invoices, and payments.

## 1) Role Defaults for New Orgs
When a new org is created, default `gl_accounts` are auto-populated for these role types:

- `rep`
- `vendor`
- `manufacturer`
- `employee`

Implementation:
- Save hook: `apps/orgs/models/base.py` (`OrgBase.save`)
- Resolver: `apps/accounts/services/gl_defaults.py` (`get_org_role_gl_defaults`)

Behavior:
- Only fills missing keys, never overwrites existing `gl_accounts` values.
- Adds a generic `activity` account for all four role types.
- Adds a role-specific key:
  - `rep` -> `commission`
  - `vendor` -> `purchase`
  - `manufacturer` -> `purchase`
  - `employee` -> `expense`

Account selection order:
1. Active `GlAccount` by `used_for` aliases (best match)
2. Fallback defaults in `FALLBACK_DEFAULTS`

## 2) Entity-Level Defaults at Creation

Newly created entities automatically receive sensible default GL accounts for typical flows (Sales, Inventory, Cost, Purchase). The following entity types receive defaults at creation time:

- Customers
- Items
- Services
- Vendors
- Manufacturers
- Reps

Defaults are assigned via a small service hook in accounts and may consult org-level configuration. If unset, a safe fallback category is applied.

### Override Priority

You can override GL accounts per record at any time. The system prefers the most specific setting:

1. Record-specific override (e.g., item-level)
2. Entity-type defaults (e.g., all services)
3. Global/org defaults

Defaults are idempotent and only applied when a record lacks explicit assignments.
Bulk imports can disable auto-defaulting and later run a reconcile to fill missing GL assignments.

### Backfill Command

```bash
python manage.py backfill_gl_defaults --limit 0
```

Related:
- Tax jurisdictions: `gl_account_payable` gets defaulted when missing.
- Contacts receiving commissions: `prefs.gl_accounts.commission` is set when absent.

## 3) Item + Primary Org Defaults
Primary org defaults are stored in setting:
- `purpose = db_defaults`
- `name = primary_organization`
- payload key: `data.default_gl_accounts`

Implementation:
- Payload builder: `apps/orgs/services/primary_org.py`
- Item default resolver: `apps/accounts/services/gl_defaults.py` (`get_item_gl_defaults`)
- Item save seed: `apps/products/models/item.py`

## 4) Invoice GL Staging
On invoice ledger processing, invoice metadata is staged with posting intent:

- Debit Accounts Receivable
- Credit Sales Revenue

Implementation:
- `apps/accounts/services/ledger_balance.py`
- Function: `_stage_invoice_gl_accounts`
- Trigger path: `on_invoice_save`

Metadata shape (invoice):
```json
{
  "gl_accounts": {
    "event": "invoice_created",
    "postings": [
      {"side": "debit", "purpose": "accounts_receivable", "account": "...", "amount": 0},
      {"side": "credit", "purpose": "sales_revenue", "account": "...", "amount": 0}
    ]
  }
}
```

Accounting rationale:
- Revenue is recognized at invoice creation (credit sale).
- This impacts P&L through revenue.

## 5) Payment GL Staging
On payment save/ledger processing, payment metadata is staged with posting intent:

- Debit Cash/Bank
- Credit Accounts Receivable

Implementation:
- `apps/accounts/services/ledger_balance.py`
- Function: `_stage_payment_gl_accounts`
- Trigger path: `on_payment_save`

Metadata shape (payment):
```json
{
  "gl_accounts": {
    "event": "payment_received",
    "postings": [
      {"side": "debit", "purpose": "cash_receipt", "account": "...", "amount": 0},
      {"side": "credit", "purpose": "accounts_receivable", "account": "...", "amount": 0}
    ]
  }
}
```

Accounting rationale:
- Payment converts one asset to another (AR -> Cash).
- No new income is recognized at payment application.

## 6) Data Sources for GL Account Resolution
Resolution utilities live in `apps/accounts/services/gl_defaults.py`:

- `get_org_role_gl_defaults(org_type)`
- `get_item_gl_defaults()`
- `get_invoice_payment_staging_defaults(...)`

Resolution priority:
1. Explicit setting/default payloads where applicable
2. Active chart of accounts (`GlAccount.used_for`)
3. `FALLBACK_DEFAULTS`

## 7) Tests
Coverage for this behavior:

- `tests/test_org_role_gl_defaults.py`
- `tests/test_gl_account_staging.py`
- `tests/test_item_gl_defaults_from_primary_org.py`
- `tests/test_orgs_primary_org_service.py`

## 8) Notes
- Staging metadata is intent/trace data and supports auditability.
- Ledger balances remain authoritative for AR state.
- Existing values are preserved where possible (non-destructive defaulting).
