# Session 2026-06-27 — Deliverables & Test Checklist

## Overview

This session built the core commerce infrastructure for wc3: pricing, inventory, GL posting, training, and admin dashboards. 85 automated tests cover the backend. This document lists everything delivered and provides a human testing checklist to verify it works end-to-end.

---

## What Was Built

### 1. Database Fix
- **DB_MODE forced to 'local'** in settings.py — prevents accidental remote database routing
- **MCP connections** to Allie and Alice (WebClerk) verified working

### 2. React25 Audit (Phase 1)
- Audited all 63+ React pages
- **20 list pages:** ALL WORKING (search, pagination, wcapi integration)
- **18 detail pages:** WORKING (full CRUD including all 7 transaction types)
- **25+ admin pages:** Intentional read-only shells
- **Fixes applied:** CurrencyList JSX error, ItemList 10-record cap, axios timeouts (30s/15s), dead constants.ts deleted, itemApi consolidated to wcapi

### 3. Price Resolution Service (Phase 3)
**File:** `apps/products/services/pricing.py`

Resolves the correct price for a customer/order/line:

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | `line.price_level` | Staff overrides price for this line |
| 2 | `header.price_level` | Order-level pricing |
| 3 | `customer.price_level` | Customer's default (retail, wholesale, etc.) |
| 4 (default) | `'base'` | Item's base price |

Quantity breaks: `item.price.qty_breaks` — sorted list of `{min_qty, unit_price}`. Highest matching break wins.

**Functions:**
- `resolve_price_level(customer_level, header_level, line_level)` → effective level
- `resolve_unit_price(item_price, level, quantity)` → Decimal unit price
- `get_price_for_line(item, customer, header_level, line_level, quantity)` → full resolution with chain transparency

### 4. Inventory Availability Service (Phase 3)
**File:** `apps/products/services/inventory_availability.py`

- `get_item_availability(item_id, warehouse_id)` → on_hand, on_so, on_po, reserved, available
- `get_item_availability_by_warehouse(item_id)` → breakdown per warehouse
- Available = on_hand − reserved (visibility aid, not a hard block)

### 5. Cross-Reference Lookup Service (Phase 3)
**File:** `apps/products/services/xref_lookup.py`

Find items by any external identifier:
- `lookup_by_external_sku(sku, source)` → by manufacturer/vendor SKU
- `lookup_by_code(code, code_type)` → by GTIN, UPC, EAN, MPN
- `find_item_by_any_identifier(identifier)` → tries ida, then xref SKU, then codes; prefers is_preferred

### 6. GL Posting & Reversals (Phase 2 + Phase 5)
**Files:** `apps/accounts/services/ledger_balance.py`, `apps/core/views/manage_view.py`

GL posting is **user-initiated** — records stay editable until explicitly journalized.

| Action | Endpoint | What happens |
|--------|----------|-------------|
| **Post to GL** | `POST /wcapi/manage/ {action: "post_gl_entries", params: {model_name, id}}` | Creates GlJournal entries from staged metadata, locks record |
| **Reverse GL** | `POST /wcapi/manage/ {action: "reverse_gl_entries", params: {model_name, id}}` | Creates contra entries (debit↔credit swapped), unlocks record |

Correction workflow: Post → Reverse → Edit → Re-post

**GlJournal model** now has `source_id` and `source_model` for traceability. Double-posting guard prevents duplicate entries.

### 7. Contact/Org Bidirectional Linking (Phase 2)
**File:** `apps/core/models/contact.py`

`save_after()` now ensures bidirectional refs: when a Contact is linked to a Customer (or Vendor, etc.), the org's `refs.links.contact` array is updated to include the contact.

### 8. RBAC Staff Authority Rules (Phase 5)
**File:** `apps/core/services/role_defaults.py`

Three operations require staff/admin authority:

| Operation | Non-staff behavior |
|-----------|--------------------|
| Change `price_level` on a line | Blocked — `edit_deny: ["price_level"]` |
| Negative quantity (returns) | Blocked — `negative_quantity: false` |
| View cost fields | Hidden — `view_deny: ["cost", ...]` |

### 9. Nightly Celery Tasks
**Files:** `apps/support/scheduler/tasks.py`, `webclerk3_api/settings.py`

| Time (UTC) | Task | What it does |
|------------|------|-------------|
| 2:40 AM | `task_reconcile_aging` | Recalculate AR aging buckets for all orgs |
| 3:40 AM | `task_audit_refs_fk` | Detect FK↔refs.links drift, log to RefsMismatchLog |

### 10. Orphan Detection Service
**File:** `apps/core/services/orphan_detection.py`

Finds records with null or dangling FKs across 15 registered parent-child relationships.

| Action | Endpoint |
|--------|----------|
| Get counts | `POST /wcapi/manage/ {action: "get_orphan_counts"}` |
| Get detail | `POST /wcapi/manage/ {action: "get_orphan_detail", params: {app, model, fk_field}}` |

### 11. Accounting Dashboard
**Backend:** `apps/accounts/services/accounting_dashboard.py`
**React page:** `/accounting`

Seven cards showing:
- GL Balance (debits vs credits, imbalance detection)
- Journal Status (last journalized, pending counts)
- AR Aging Summary (current/30/60/90+ buckets)
- Transaction Volume (counts by type + status)
- Locked Records (journalized vs editable)
- Pending Inventory (unprocessed count + age)
- Orphan Detection (FK integrity)

### 12. Alice Training System
**Backend:** `apps/transactions/services/training_flow.py`
**Seed command:** `apps/transactions/management/commands/seed_training_data.py`
**React page:** `/training`

Guided 6-step commerce cycle using zzitem + zzCustomer:
1. Create Proposal (no inventory effect)
2. Convert to Order (on_so increases)
3. Invoice/Ship (on_hand decreases, on_so decreases)
4. Record Payment (financial, no inventory)
5. Purchase Order (on_po increases)
6. Receive Goods (on_hand increases, on_po decreases)

All records flagged `metadata.training=True`. Cleanup removes training data. Reports exclude via `WHERE ida NOT LIKE 'zz%'` or `.exclude(metadata__training=True)`.

### 13. React Toolbar Buttons
**File:** `React2025/src/apps/common/components/TransactionToolbar.tsx`

- **Post GL** button — visible when record is unlocked, calls `onPostGL`
- **Reverse GL** button — visible when record is locked, calls `onReverseGL`

### 14. Data Integrity Tests (Phase 6)
- Export/import roundtrip with FK integrity verification
- RefsMismatchLog detection (null, dangling, both_differ types)
- Soft delete exclusion from default queries
- Version conflict detection via `assert_version`

### 15. Translation Plan
**File:** `readmes/wc2-wc3-translation-plan.md`

Comprehensive plan covering:
- 38 tasks across 6 phases with difficulty weights and unit tests
- Architecture decisions (import, export, admin, sync, hooks, Athena)
- Dropped ~405 of ~460 wc2 methods with rationale
- Deferred features list

---

## Automated Tests

**Run all 85 session tests:**
```bash
cd webClerk3
./bin/python -m pytest tests/task_2026_06_27.py -v --no-cov
```

**Run by area:**
```bash
# GL posting + reversals (10 tests)
./bin/python -m pytest tests/test_gl_posting.py tests/test_gl_manage_action.py -v --no-cov

# Pricing (17 tests)
./bin/python -m pytest tests/test_pricing.py -v --no-cov

# Inventory + cross-reference (13 tests)
./bin/python -m pytest tests/test_inventory_and_xref.py -v --no-cov

# Inventory bucket flow (4 tests)
./bin/python -m pytest tests/test_inventory_bucket_flow.py -v --no-cov

# Commerce cycle e2e (6 tests)
./bin/python -m pytest tests/test_commerce_cycle_e2e.py -v --no-cov

# Data integrity (9 tests)
./bin/python -m pytest tests/test_data_integrity.py -v --no-cov

# Training flow (6 tests)
./bin/python -m pytest tests/test_training_flow.py -v --no-cov

# Orphan detection (7 tests)
./bin/python -m pytest tests/test_orphan_detection.py -v --no-cov

# Accounting dashboard (7 tests)
./bin/python -m pytest tests/test_accounting_dashboard.py -v --no-cov
```

---

## Human Testing Checklist

### Prerequisites
- [ ] Django server running: `./runserver.sh local`
- [ ] React dev server running: `npm run dev` in React2025
- [ ] Database has data: `./bin/python manage.py seed_training_data`
- [ ] Logged in as superuser (claude@jpods.com or bill@local.com)

### A. React List Pages
- [ ] Navigate to Orders list — records load, search works, pagination works
- [ ] Navigate to Invoices list — records load, status badges display
- [ ] Navigate to Customers list — records load, click opens detail
- [ ] Navigate to Items list — full record set loads (not capped at 10)
- [ ] Navigate to Currencies list — renders without JSX error

### B. React Detail Pages
- [ ] Open an Order detail — loads header + line items
- [ ] Add a line item to an order — item search works, price populates
- [ ] Save the order — totals recalculate, toast confirms save
- [ ] Open a Customer detail — all fields editable, save works
- [ ] Open an Invoice detail — lines display, Transfer button works

### C. Price Resolution
- [ ] Create an order for a customer with `price_level = 'wholesale'`
- [ ] Add zzitem — verify price shows $20.00 (wholesale), not $25.00 (base)
- [ ] Change line quantity to 50 — verify price drops to $20.00 (qty break)
- [ ] As non-admin user, verify `price_level` field is not editable on the line

### D. Inventory Availability
- [ ] Open zzitem detail — verify inventory shows on_hand = 100
- [ ] After running training flow, verify on_hand changes reflect

### E. GL Posting Workflow
- [ ] Create an invoice with line items
- [ ] In Django admin or via API: verify `metadata.gl_accounts` has staged postings
- [ ] Call `POST /wcapi/manage/ {action: "post_gl_entries", params: {model_name: "invoice", id: <id>}}`
- [ ] Verify: GlJournal records created (check Django admin: GL Journals)
- [ ] Verify: Invoice is now locked (`is_locked = True`)
- [ ] Call `POST /wcapi/manage/ {action: "reverse_gl_entries", params: {model_name: "invoice", id: <id>}}`
- [ ] Verify: Contra entries created, invoice unlocked

### F. Accounting Dashboard
- [ ] Navigate to `/accounting`
- [ ] Verify: GL Balance card shows debits vs credits
- [ ] Verify: Journal Status shows entry count + pending
- [ ] Verify: Transaction Volume shows counts by type
- [ ] Verify: Refresh button reloads data
- [ ] Verify: Orphan detection card shows clean or lists issues

### G. Alice Training Flow
- [ ] Run: `./bin/python manage.py seed_training_data`
- [ ] Navigate to `/training`
- [ ] Verify: zzitem and zzCustomer found automatically
- [ ] Adjust quantities (e.g., proposal=5, order=4, invoice=3, PO=10, receive=8)
- [ ] Click "Run Full Cycle"
- [ ] Verify: All 6 steps complete
- [ ] Click each step — verify inventory bars update with deltas (+/-)
- [ ] Read Alice's coaching text — verify it explains what happened
- [ ] Verify: on_hand changed only on Invoice (decrease) and Receive (increase)
- [ ] Verify: on_so changed only on Order (increase) and Invoice (decrease)
- [ ] Verify: on_po changed only on PO (increase) and Receive (decrease)
- [ ] Click "Cleanup" — verify training records removed

### H. Data Integrity
- [ ] In Django admin, verify RefsMismatchLog table exists
- [ ] Run: `./bin/python manage.py reconcile_financials --dry-run`
- [ ] Verify orphan detection: `POST /wcapi/manage/ {action: "get_orphan_counts"}`
- [ ] If orphans found, investigate with: `POST /wcapi/manage/ {action: "get_orphan_detail", params: {app, model, fk_field}}`

### I. Conversion Chain
- [ ] Create a proposal with zzitem
- [ ] On proposal detail, click Transfer → Order
- [ ] Verify: New order opens pre-populated with proposal lines
- [ ] Save the order
- [ ] On order detail, click Transfer → Invoice
- [ ] Verify: New invoice opens pre-populated with order lines

### J. Cross-Reference Lookup
- [ ] In Django admin, create an ItemXRef for zzitem with external_sku = "MFR-12345"
- [ ] Via API: `POST /wcapi/manage/` or test in Python shell:
  ```python
  from apps.products.services.xref_lookup import find_item_by_any_identifier
  result = find_item_by_any_identifier("MFR-12345")
  # Should return zzitem
  ```

---

## User Learning Checklist

Complete these exercises in order. Each builds on the previous. Check the box when you can explain it to someone else.

### Lesson 1: How Inventory Moves
_Goal: Understand that inventory only changes when goods physically move_

- [ ] Go to `/training` and run the full cycle with default quantities
- [ ] **I can explain:** Why does a proposal NOT change on_hand?
- [ ] **I can explain:** Why does an order increase on_so but NOT decrease on_hand?
- [ ] **I can explain:** What happens to on_hand and on_so when we invoice?
- [ ] **I can explain:** Why does a payment have ZERO inventory effect?
- [ ] **I can explain:** What's the difference between on_hand and available?
- [ ] Change the quantities and run again — predict the results before clicking

### Lesson 2: How Pricing Works
_Goal: Understand the price level chain_

- [ ] Create a customer with `price_level = 'wholesale'`
- [ ] Add zzitem to an order for that customer
- [ ] **I can explain:** Why did the price show $20.00 instead of $25.00?
- [ ] **I can explain:** What happens if I change the line's price_level to 'sample'?
- [ ] **I can explain:** Who is allowed to change price_level on a line? Why?
- [ ] Add 50 units — **I can explain:** why did the unit price change? (quantity break)

### Lesson 3: How Journalizing Works
_Goal: Understand why records lock and how corrections work_

- [ ] Create an invoice with line items
- [ ] Post it to GL (via API or future button)
- [ ] **I can explain:** Why can't I edit this invoice now?
- [ ] **I can explain:** What are the two GL entries that were created?
- [ ] Reverse the GL entries
- [ ] **I can explain:** Why does reversal create NEW entries instead of deleting the old ones?
- [ ] **I can explain:** Why is the invoice editable again after reversal?
- [ ] Edit the invoice, re-post — **I can explain:** the full correction workflow

### Lesson 4: How the Conversion Chain Works
_Goal: Understand the proposal → order → invoice pipeline_

- [ ] Create a proposal for zzitem, qty=10
- [ ] Transfer to Order, qty=8 (partial conversion)
- [ ] Transfer Order to Invoice, qty=5 (partial fulfillment)
- [ ] **I can explain:** Where did the remaining 3 units on the order go?
- [ ] **I can explain:** What's the difference between Transfer and Clone?
- [ ] **I can explain:** Why does the invoice show `parent_id` pointing to the order?

### Lesson 5: How the Dashboard Tells You System Health
_Goal: Read the accounting dashboard and know what to worry about_

- [ ] Go to `/accounting`
- [ ] **I can explain:** What does "GL Balanced" mean? What if it says "IMBALANCED"?
- [ ] **I can explain:** What are "pending invoices" and why should I care?
- [ ] **I can explain:** What does "oldest pending age > 5 min" mean?
- [ ] **I can explain:** What is an orphan record and why is it a problem?
- [ ] **I can explain:** What does AR aging tell me about my customers?

### Lesson 6: Admin Tools
_Goal: Know when to use Django admin vs React vs psql_

- [ ] Open Django admin (`/admin/`) — browse GL Journals, see the entries you created
- [ ] **I can explain:** Why do changes in Django admin skip some audit logging?
- [ ] **I can explain:** When should I use psql instead of Django admin?
- [ ] **I can explain:** What is the "training" flag and how do reports exclude training data?

### Lesson 7: Cross-Reference Lookup
_Goal: Find an item by any identifier_

- [ ] In Django admin, add an ItemXRef for zzitem: source=manufacturer, external_sku=MFR-12345
- [ ] In Python shell: `find_item_by_any_identifier("MFR-12345")` — verify it finds zzitem
- [ ] In Python shell: `find_item_by_any_identifier("zzitem")` — verify it finds by ida
- [ ] **I can explain:** What's the lookup order? (ida → external_sku → codes)
- [ ] **I can explain:** What does "is_preferred" mean on a cross-reference?

---

## Architecture Decisions Made This Session

| Decision | Rationale |
|----------|-----------|
| DB_MODE hardcoded to 'local' | Env var override silently routed to remote DB |
| GL posting is user-initiated | Records must be editable until explicitly journalized |
| Tax/shipping are fixed values | API providers (Avalara, TaxJar) deferred until offered |
| Import = External Mandated | wc3 carries zero import code; external scripts conform to wcapi |
| Export = API + management command | Formatted exports via API; bulk dumps via management command |
| Admin = Django admin + psql | No React admin rebuild; bypass warning documented |
| Sync = compliance boundary | Trading partner data scrubbed via Connection.rules |
| refs/metadata secondary to PKs | Denormalized caches; FK wins on conflict |
| Backend is source of truth | React displays; server validates and decides |
| Pending = inventory mechanism | Line save → Pending → Celery 30s → InventoryLayer |
| Staff authority via RBAC | Negative qty, price_level, cost visibility require staff |
| Save hooks = TallyMaster | User-defined executables in Setting records |
| "zz" prefix for training | zzitem, zzCustomer — immediately filterable from reports |
| Test against PostgreSQL | SQLite JSON/FK differences waste debugging time |

---

## Files Created/Modified

### New Files (Backend)
| File | Purpose |
|------|---------|
| `apps/products/services/pricing.py` | Price resolution service |
| `apps/products/services/inventory_availability.py` | Inventory availability |
| `apps/products/services/xref_lookup.py` | Cross-reference lookup |
| `apps/transactions/services/training_flow.py` | Alice training flow |
| `apps/transactions/management/commands/seed_training_data.py` | zzitem/zzCustomer seed |
| `apps/accounts/services/accounting_dashboard.py` | Dashboard data service |
| `apps/core/services/orphan_detection.py` | Orphan FK detection |
| `tests/task_2026_06_27.py` | Session test runner (85 tests) |
| `tests/test_gl_posting.py` | GL posting tests (6) |
| `tests/test_gl_manage_action.py` | GL manage action tests (10) |
| `tests/test_commerce_cycle_e2e.py` | Commerce cycle tests (6) |
| `tests/test_pricing.py` | Price resolution tests (17) |
| `tests/test_inventory_and_xref.py` | Inventory + xref tests (13) |
| `tests/test_inventory_bucket_flow.py` | Bucket flow tests (4) |
| `tests/test_data_integrity.py` | Data integrity tests (9) |
| `tests/test_training_flow.py` | Training flow tests (6) |
| `tests/test_orphan_detection.py` | Orphan detection tests (7) |
| `tests/test_accounting_dashboard.py` | Dashboard tests (7) |
| `readmes/wc2-wc3-translation-plan.md` | Translation plan |
| `readmes/react25-audit-results.md` | React audit results |
| `readmes/session-2026-06-27-deliverables.md` | This document |

### New Files (React)
| File | Purpose |
|------|---------|
| `pages/admin/AccountingDashboard.tsx` | Accounting dashboard page |
| `pages/admin/AliceTraining.tsx` | Training flow page |

### Modified Files (Backend)
| File | Change |
|------|--------|
| `webclerk3_api/settings.py` | DB_MODE forced local, 3 Celery tasks |
| `apps/accounts/models/gl_journal.py` | source_id, source_model fields |
| `apps/accounts/models/__init__.py` | GlJournal export |
| `apps/accounts/services/ledger_balance.py` | post_staged_gl_entries, reverse_gl_entries |
| `apps/core/models/contact.py` | save_after bidirectional refs |
| `apps/core/views/manage_view.py` | 6 new manage actions |
| `apps/core/services/role_defaults.py` | Staff authority restricted_fields |
| `apps/transactions/services/transaction_save.py` | Tax/shipping comment |
| `apps/support/scheduler/tasks.py` | Aging + refs audit tasks |
| `tests/conftest.py` | Fixed ContactFactory, WarehouseFactory |

### Modified Files (React)
| File | Change |
|------|--------|
| `src/apps/common/components/TransactionToolbar.tsx` | Post GL / Reverse GL buttons |
| `src/apps/accounts/models/currency/pages/CurrencyList.tsx` | JSX fix |
| `src/apps/products/models/item/pages/ItemList.tsx` | Removed 10-record cap |
| `src/apps/products/models/item/services/itemApi.ts` | wcapi consolidation |
| `src/api/axios.ts` | Request timeouts |
| `src/api/constants.ts` | Deleted (dead code) |
| `src/routes/Routes.ts` | accounting + training routes |
| `src/routes/protectedRoutesConfig.tsx` | Dashboard + training page routes |
