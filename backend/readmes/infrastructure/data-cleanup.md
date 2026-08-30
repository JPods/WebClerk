# Remote Database Data Cleanup

**Date:** February 2026  
**Target:** `76.13.185.210:5432/commerce_expert`

## Overview

A comprehensive data quality audit was performed on the remote PostgreSQL database covering all 82 tables (~1,400 records). Three categories of issues were identified and resolved.

---

## 1. NULL UUIDs

**Problem:** 25 tables had every UUID set to `NULL` (~763 records total). UUIDs are required for `sync_model` conflict detection — without them, the sync command cannot distinguish between matching records and true conflicts.

**Tables affected:**
`actions`, `contacts`, `domains`, `emails`, `invoices`, `invoice_lines`, `locations`, `orders`, `order_lines`, `orgs_orgbase`, `pending`, `phones`, `products_billofmaterial`, `products_inventorylayer`, `products_inventorymovement`, `products_item`, `products_serial`, `products_siteinventory`, `products_warehouse`, `proposals`, `proposal_lines`, `settings`, `templates`, `work_orders`, `work_order_lines`

**Fix:** Populated all NULL UUIDs using `gen_random_uuid()` in a single transaction.

```sql
BEGIN;
UPDATE actions SET uuid = gen_random_uuid() WHERE uuid IS NULL;
UPDATE contacts SET uuid = gen_random_uuid() WHERE uuid IS NULL;
-- ... (all 25 tables)
COMMIT;
```

**Script:** `tools/populate_uuids_simple.sql`

---

## 2. Orphaned `actions.contact_id`

**Problem:** 123 action records referenced non-existent contacts:

| contact_id | Count | Nature |
|---|---|---|
| 0 | 82 | Placeholder value (no contact with id=0 exists) |
| 3 | 23 | Deleted developer/team contact |
| 15 | 11 | Deleted developer/team contact |
| 17 | 7 | Deleted developer/team contact |

All 123 records were internal development/project tasks (e.g., "Login", "Install Celery", "Kanban columns in wrong order"), not customer-facing data.

**Constraint:** `contact_id` has a `NOT NULL` constraint, so NULLing was not an option.

**Fix:** Remapped all 123 orphaned records to `contact_id = 1` (the first valid contact).

```sql
BEGIN;
UPDATE actions
SET contact_id = 1
WHERE contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = actions.contact_id);
COMMIT;
```

**Script:** `tools/fix_orphan_actions.sql`

---

## 3. `_id_id` Column Naming

**Problem:** Three tables had malformed FK column names caused by a legacy Django migration pattern:

| Table | Bad Column | Corrected Column |
|---|---|---|
| `invoice_lines` | `invoice_id_id` | `invoice_id` |
| `proposal_lines` | `proposal_id_id` | `proposal_id` |
| `work_order_lines` | `workorder_id_id` | `workorder_id` |

**Fix:** Columns renamed via `ALTER TABLE ... RENAME COLUMN`. Related code in `fetch_order.py` and `tools/inventory_tester.py` was updated to remove legacy `_id_id` fallback logic.

---

## Verification

All three checks return **0** after cleanup:

```bash
# NULL UUIDs
psql -c "SELECT count(*) FROM order_lines WHERE uuid IS NULL;"
# → 0

# Orphaned actions.contact_id
psql -c "SELECT count(*) FROM actions a
  WHERE a.contact_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = a.contact_id);"
# → 0

# _id_id columns
psql -c "SELECT count(*) FROM information_schema.columns
  WHERE table_schema='public' AND column_name LIKE '%_id_id';"
# → 0
```

**Verification script:** `tools/verify_cleanup.py`

---

## Tools Created

| File | Purpose |
|---|---|
| `tools/populate_uuids_simple.sql` | Populate NULL UUIDs with `gen_random_uuid()` |
| `tools/fix_orphan_actions.sql` | Remap orphaned `actions.contact_id` to contact 1 |
| `tools/remote_audit.sql` | Full remote database audit (duplicates, NULLs, orphans, gaps) |
| `tools/remote_fk_check.sql` | FK orphan checks with correct column names |
| `tools/verify_cleanup.py` | Python script to verify all three cleanup checks pass |

## Other Audit Findings (No Action Required)

- **PK sequence gaps** — `emails` table has a 617-record gap, `products_item` has a 150-record gap. These are harmless and typical of deleted test data.
- **All other FK relationships** — Clean. No orphans outside of `actions.contact_id`.
