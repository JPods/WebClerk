# PJPV Shadow Field Removal — 2026-08-24

## What Happened

Removed all 12 scalar shadow fields from WC3 models. These fields duplicated values
from JSON envelopes to support Django ORM queries (`filter()`, `Sum()`, `ORDER BY`).
They violated PJPV's core rule: JSON is the single source of truth.

## What Was Removed

### TransactionBaseModel (`apps/transactions/models/base_transaction_model.py`)
| Field | Type | JSON Source |
|-------|------|------------|
| `total` | DecimalField | `totals.total` |
| `balance` | DecimalField | `totals.balance` |
| `company` | CharField | customer.display_name |
| `address_full` | CharField | refs.links display cache |
| `email` | EmailField | refs.links display cache |
| `phone` | CharField | refs.links display cache |

### OrgBase (`apps/orgs/models/base.py`)
| Field | Type | Source |
|-------|------|--------|
| `address_full` | CharField | Address record via address_id FK |
| `phone` | CharField | Phone record via phone_id FK |
| `domain` | CharField | Domain record via domain_id FK |

### Contact (`apps/core/models/contact.py`)
| Field | Type | Source |
|-------|------|--------|
| `address_full` | CharField | Address record via address_id FK |
| `phone` | CharField | Phone record via phone_id FK |
| `domain` | CharField | Domain record via domain_id FK |

### Fields Kept (not shadows)
- `Contact.email` — USERNAME_FIELD for auth, unique constraint
- `OrgBase.email` — primary identifier, user-entered
- `TransactionBaseModel.source_name` — standalone dropdown, not a shadow
- All `*_id` FK pointer fields (`address_id`, `email_id`, `phone_id`, `domain_id`)

## What Replaced Them

### 1. PostgreSQL Functional Indexes (search/filter)
Migration `0001_initial` includes functional indexes on JSON paths:
```sql
CREATE INDEX idx_invoice_totals_total ON invoices (((totals->>'total')::numeric));
CREATE INDEX idx_invoice_totals_balance ON invoices (((totals->>'balance')::numeric));
-- Same for orders, proposals, purchases, work_orders
```

Django ORM queries use `common/json_lookups.py` helpers:
```python
from common.json_lookups import totals_total, totals_balance

Invoice.objects.annotate(_bal=totals_balance()).filter(_bal__gt=0)
Invoice.objects.annotate(_total=totals_total()).aggregate(s=Sum('_total'))
```

### 2. Alice Aggregate Collections (dashboard Sum())
`apps/ai_assistant/services/aggregate_tracker.py` — Alice maintains aggregate
values in Setting records (`purpose='alice:aggregates'`).

- **Delta updates**: post_save signal on each transaction model. When `totals`
  changes, Alice computes the difference and adjusts the cached aggregate atomically.
- **Periodic refresh**: `python manage.py refresh_aggregates` — full recompute
  from DB using JSON path queries. Corrects any accumulated drift.
- **Drift is acceptable**: Dashboard totals are non-critical display values.
  Real-time accuracy not required.

Signal wiring is at the bottom of `apps/transactions/signals.py`:
- `_stash_old_totals` (pre_save) — reads current totals for delta computation
- `_apply_aggregate_delta` (post_save) — applies delta to Alice's Setting

### 3. @property Methods (backward compat for admin/serializers)
Each removed field has a read-only `@property` on the model that reads from
the JSON envelope or FK relationships:

- `TransactionBaseModel.total` → reads `self.totals['total']`
- `TransactionBaseModel.balance` → reads `self.totals['balance']`
- `TransactionBaseModel.company` → reads `self.customer.display_name`
- `TransactionBaseModel.email` → reads `self.contact.email` or `refs.links`
- `TransactionBaseModel.phone` → reads from `refs.links`
- `TransactionBaseModel.address_full` → reads from `refs.links`
- `OrgBase.address_full` → reads Address record via `address_id` FK
- `OrgBase.phone` → reads Phone record via `phone_id` FK
- `OrgBase.domain` → reads Domain record via `domain_id` FK
- `Contact.address_full` → reads Address record via `address_id` FK
- `Contact.phone` → reads Phone record via `phone_id` FK
- `Contact.domain` → reads Domain record via `domain_id` FK or extracts from email

## Dual-Write Removed

`apps/transactions/services/totals.py` — the totals engine no longer writes
to scalar fields. Two locations cleaned:

1. `recalculate_totals()` — removed `header.total = _d(total)` and
   `header.balance = _d(balance)`. update_fields now `['totals']` only.
2. `update_received()` — same removal. JSON envelope is the only write target.

## Contact Sync Simplified

`Contact._sync_primary_communication_links()` was updated:
- Before: synced email, phone, domain, address_full scalars → communication records
- After: syncs only email (the remaining scalar) → Email records
- Still rebuilds `refs.links` from all communication tables
- Phone, domain, address editing now happens directly on communication records

## Bug Fixed

`apps/core/services/commerce_dashboard.py` line 308 had `Sum('total')` on Payment.
Payment has no `total` field — it has `amount`. Changed to `Sum('amount')`.

## Dashboard Queries Migrated

All `Sum('total')`, `Sum('balance')`, `filter(balance__gt=0)` calls converted to
JSON path queries using `common/json_lookups.py` helpers:

| File | What Changed |
|------|-------------|
| `commerce_dashboard.py` | Sum('total') on Order/Invoice/Proposal, Sum('balance') for AR aging |
| `collections_dashboard.py` | Sum('total') for DSO, Sum('balance') for open invoices |
| `sales_pipeline.py` | 6x Sum('total') across proposal/order/invoice stages |
| `vendor_summary.py` | Sum('total') on Purchase |
| `credit_check.py` | Sum('total') on Order backlog, filter(total__isnull=False) |
| `accounting_watchdog.py` | filter(total__isnull=False) |
| `aged_receivables.py` | Sum('total') on Order per customer |
| `ledger_balance.py` | Sum('total') on Order open exposure |
| `import_wc2.py` | Sum('balance') on Invoice verification |

## work_order -> workorder Rename

Also renamed the model registry key from `work_order` to `workorder` to match
Django's `_meta.model_name` (no underscore). DB table `work_orders` unchanged.

- Model registry key: `workorder` (was `work_order`)
- ~21 backend files updated in seed commands, services, views
- Existing Setting/Report DB records updated
- All `work_order` references cleaned up (2026-08-24 scrub)

## Files Created

| File | Purpose |
|------|---------|
| `common/json_lookups.py` | `totals_total()`, `totals_balance()`, `totals_received()` ORM helpers |
| `apps/ai_assistant/services/aggregate_tracker.py` | Alice aggregate collections with delta updates |
| `apps/ai_assistant/management/commands/refresh_aggregates.py` | Nightly drift correction command |

## Migrations

All migrations were deleted and regenerated fresh from current model state.
The DB has the correct schema; migrations were fake-applied.

---

## Scrub Checklist — Completed 2026-08-24

All items verified clean by post-fix PJPV scrub.

| # | Item | Status | Date |
|---|------|--------|------|
| 1 | `work_order` → `workorder` rename (backend ~25 files, frontend ~15 files, docs ~15 files) | **Done** | 2026-08-24 |
| 2 | No scalar shadow field queries remain | **Clean** | 2026-08-24 |
| 3 | @property backward compat verified | **Clean** | 2026-08-24 |
| 4 | Alice aggregates | Verify with `python manage.py refresh_aggregates` | — |
| 5 | Functional indexes | Verify with `pg_indexes` query | — |
| 6 | Frontend `work_order` references | **Done** | 2026-08-24 |
| 7 | Denormalized fields registry updated | **Done** | 2026-08-24 |
| 8 | Alice code scanner patterns | Alice manages | — |
| 9 | Banned dict keys (`total_amount`/`margin_amount`) → `total`/`margin` | **Done** | 2026-08-24 |
| 10 | Serializer duplication (`total`/`balance` removed from fields) | **Done** | 2026-08-24 |
| 11 | `refresh_from_db` fixed (only `['totals']`) | **Done** | 2026-08-24 |
| 12 | `status_guard.py` FK field name fixed (`workorder_id`) | **Done** | 2026-08-24 |
| 13 | Stale doc references (6 readme files) | **Done** | 2026-08-24 |
