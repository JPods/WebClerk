# Database Maintenance

<!-- TOC START -->

## Table of Contents

- [Database Maintenance](#database-maintenance)
  - [Table of Contents](#table-of-contents)
  - [ID Conventions](#id-conventions)
    - [Rule: id = 0 means "new record"](#rule-id--0-means-new-record)
    - [Backend enforcement](#backend-enforcement)
    - [Frontend enforcement](#frontend-enforcement)
    - [Audit query](#audit-query)
  - [Daily Org Financial Integrity Log](#daily-org-financial-integrity-log)

<!-- TOC END -->

Date: 2025-02-18
Status: Active
Owner: Bill

## ID Conventions

### Rule: id = 0 means "new record"

All tables use an auto-incrementing `id` (BigAutoField) as the primary key.
The values `id = 0`, `id = null`, or the absence of `id` all signify a **new, unsaved record**.

**No database row should ever have `id = 0`.**

PostgreSQL's sequences start at 1 by default, so `id = 0` should never occur
organically. If a row with `id = 0` exists, it was created by a bug that
explicitly passed `id=0` to an `INSERT` or `objects.create()` call.

| Value        | Meaning                          |
|--------------|----------------------------------|
| `id > 0`     | Existing persisted record        |
| `id = 0`     | New / unsaved (treat as no id)   |
| `id = null`  | New / unsaved                    |
| `id` absent  | New / unsaved                    |

### Backend enforcement

`save_transaction_with_lines` (and any service that creates records) **must**
strip a falsy `id` before calling `Model.objects.create()`:

```python
if not header_id:
    header_clean.pop('id', None)   # let the DB assign the next sequence value
```

The generic `filter_input_fields` helper also ignores `id` when its value is
falsy, preventing `0` from leaking into `INSERT` statements.

### Frontend enforcement

When building a record payload for save, omit `id` entirely for new records
rather than sending `id: 0`:

```typescript
// correct — omit id on create
const payload = rawId ? { id: rawId, ...fields } : { ...fields };

// wrong — sends id: 0 to the backend
const payload = { id: data?.id ?? 0, ...fields };
```

### Audit query

Run periodically (or after a migration) to verify no rows have `id = 0`:

```sql
-- Check all transaction tables for id = 0
SELECT 'orders'    AS tbl, id FROM orders     WHERE id = 0
UNION ALL
SELECT 'invoices'  AS tbl, id FROM invoices   WHERE id = 0
UNION ALL
SELECT 'proposals' AS tbl, id FROM proposals  WHERE id = 0
UNION ALL
SELECT 'purchases' AS tbl, id FROM purchases  WHERE id = 0
UNION ALL
SELECT 'workorders' AS tbl, id FROM workorders WHERE id = 0;
```

If any rows are returned, investigate the source and either reassign a valid
sequence id or delete the rogue row after confirming it holds no real data.

## Daily Org Financial Integrity Log

Run this command daily to keep org financial records synchronized and create an auditable observation record:

```bash
python manage.py org_financial_maintenance --mode daily --activity-hours 24
```

What this daily run covers:

- Ages receivables/payables into org financial records for customer/vendor orgs.
- Accounts for recent transaction activity in org-level financial snapshots.
- Processes queued pending org-financial updates created when records were locked.
- Writes a daily `alice_log` health-check record with unusual conditions that need follow-up.

The daily observation highlights:

- `locked_queued`, `locked_skipped`
- `scrub_errors`, `pending_errors`, `missing_org`
- per-model transaction activity counts in the selected window

Useful variants:

```bash
# Preview only
python manage.py org_financial_maintenance --mode daily --dry-run

# Narrow to one org type
python manage.py org_financial_maintenance --mode daily --org-type customer

# Skip writing the Alice observation (not recommended for daily runs)
python manage.py org_financial_maintenance --mode daily --no-alice-log
```
