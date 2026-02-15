# Refs ↔ FK Coexistence Audit Report

**Date:** February 15, 2026  
**Scope:** All `.refs` JSONField usage across `apps/`, `common/refs/`, model services, views  
**Context:** 48 FK fields were renamed across 20 model files (`_id` suffix dropped)

---

## 1. Overall Refs Architecture (`common/refs/`)

The `refs` JSONField is a `models.JSONField` present on every model inheriting `BaseModel` via `RefsMixin`. Its default structure (from `common/models.py:306`):

```python
{
    "keywords": [],      # denormalized searchable keywords
    "tags": [],           # user-created tags
    "links": {"contact": [], "item": []},  # denormalized relationship buckets
    "parents": [],        # Gantt dependency IDs (action parent→child)
    "depends_on": {},     # execution gating: {"action": [1,2], "work_order": [5]}
    "categories": [],
    "related_ids": [],
}
```

### Subsystem Responsibilities

| File | Purpose |
|------|---------|
| `common/refs/links.py` | `upsert_link()`, `remove_link()`, `ensure_bidirectional()` — manages `refs.links` buckets (both legacy list-of-dicts and newer dict-of-buckets format) |
| `common/refs/contact_refs.py` | `normalize_refs_for_save()` / `normalize_refs_for_response()` — enriches `refs.links.contact` entries with denormalized contact fields (email, phone, address, attention) |
| `common/refs/policy.py` | `PolicyEngine` with `RefsRule` — time- and count-based pruning rules for `refs.links` entries (e.g., drop invoice_line links older than 30 days) |
| `common/refs/tasks.py` | `prune_refs_for_owner()`, `nightly_prune_refs()`, `sync_assignees_for_line()`, `nightly_backfill_assignee_refs()`, `sync_action_denorm_refs()` — scheduled maintenance |
| `common/refs/assignees.py` | `ensure_line_assignee_links()` — iterates open Actions on a line and ensures bidirectional refs to each assignee party |
| `common/refs/actions_index.py` | `ensure_action_target_links()`, `ensure_action_all_links()` — ensures bidirectional refs between an Action and all its relational/GenericFK targets |
| `common/models.py` `RefsMixin` | `add_keyword()`, `add_tag()`, `denormalize_links()`, `ensure_links_denormalized()` — base model helpers |

### Key Design Principle

`refs.links` was designed as a **denormalization layer** — a JSON cache of related IDs that can be queried via PostgreSQL JSON operators (`refs__links__contact__contains`). It was never meant to be the **source of truth** for relationships; that role should belong to FK fields. The `RefsMismatchLog` model and endpoint exist specifically to detect and track divergences.

---

## 2. Files Where `.refs` Stores Relationship Data That DUPLICATES an FK

These are the highest-priority findings — places where both a proper FK and a `refs` entry track the same relationship.

### 2.1 Payment → Invoice (DUPLICATE)

**FK exists:** `Payment.invoice` FK → `Invoice` (defined in `apps/transactions/models/payment.py:66`)  
**refs also stores:** `payment.refs['invoice_ids']` — a *list* of invoice IDs

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/models/payment.py` | L7-13 | `default_refs()` initializes `{"invoice_ids": [], "order_ids": [], "source": {...}}` |
| `apps/transactions/models/payment.py` | L190-196 | `add_invoice_ref()` appends to `refs['invoice_ids']` |
| `apps/transactions/services/payment_application.py` | L78 | `payment.add_invoice_ref(invoice.id)` — writes invoice ID into refs **after** the FK already links them |
| `apps/transactions/views/payment_views.py` | L311 | Reads `payment.refs.get('invoice_ids', [])` to iterate invoices (could use `PaymentApplication` join or FK) |
| `apps/transactions/tests/test_payment_models.py` | L92-98 | Tests assert on `refs['invoice_ids']` |
| `apps/transactions/tests/test_payment_services.py` | L57 | Tests assert on `refs['invoice_ids']` |
| `apps/transactions/tests/test_payment_integration.py` | L84 | Tests assert on `refs['invoice_ids']` |

**Analysis:** The FK (`Payment.invoice`) points to a single primary invoice. The `refs['invoice_ids']` list is a many-to-many pattern (one payment can apply to multiple invoices). However, there's also a `PaymentApplication` junction table with `payment` FK and `invoice` FK. This means the `refs['invoice_ids']` list is **fully redundant** with the `PaymentApplication` table and should be deprecated.

### 2.2 Invoice ← Order (DUPLICATE via source lineage)

**FK exists:** `TransactionBaseModel` has `parent_id` + `parent_model` polymorphic FK, plus the `source` JSONField  
**refs also stores:** `invoice.refs['source']['order_id']`

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/services/order_to_invoice.py` | L86 | `inv_refs.setdefault("source", {})["order_id"] = order.id` |
| `apps/transactions/services/order_to_invoice.py` | L119-128 | `_prepare_invoice_refs()` sets `refs.source.converted_from`, `refs.source.original_id`, `refs.source.invoice_type` |
| `apps/transactions/models/invoice.py` | L12 | `refs` help_text says "References like order_id" |
| `apps/transactions/tests/test_invoice_services.py` | L124 | Asserts `invoice.refs['source']['order_id'] == self.order.id` |
| `apps/transactions/tests/test_invoice_models.py` | L40 | `invoice.refs["order_id"]` set directly in test |

**Analysis:** The base transaction model now has a proper `source` JSONField (at `base_transaction_model.py:183`) and `parent_id`/`parent_model` fields. The `refs['source']['order_id']` is duplicating lineage data that could live in the dedicated `source` column.

### 2.3 Purchase ← Order/Proposal/Invoice (DUPLICATE via source lineage)

**FK exists:** `parent_id` + `parent_model` on `TransactionBaseModel`, plus `source` JSONField on base  
**refs also stores:** `refs.source.sales_order_id`, `refs.source.proposal_id`, `refs.source.invoice_id`, `refs.source.purchase_order_id`

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/services/order_to_purchase.py` | L52 | `refs={"source": {"sales_order_id": order.id}}` |
| `apps/transactions/services/proposal_to_purchase.py` | L29 | `refs={"source": {"proposal_id": proposal.id}}` |
| `apps/transactions/services/invoice_to_purchase.py` | L29 | `refs={"source": {"invoice_id": invoice.pk}}` |
| `apps/transactions/services/purchase_to_invoice.py` | L29 | `refs={"source": {"purchase_order_id": purchase.id}}` |
| `apps/transactions/services/purchase_to_order.py` | L29 | `refs={"source": {"purchase_order_id": purchase.id}}` |
| `apps/transactions/services/purchase_to_proposal.py` | L29 | `refs={"source": {"purchase_order_id": purchase.id}}` |
| `apps/transactions/services/proposal_to_order.py` | L168 | `"refs": {"source": {"proposal_id": proposal.id}}` |
| `apps/transactions/tests/test_purchase_order_services.py` | L173 | Assert `po.refs['source']['sales_order_id'] == self.order.id` |

**Analysis:** Every transfer service writes the source transaction ID into `refs.source.*_id`. The base model now has a dedicated `source = models.JSONField(...)` column **plus** `parent_id`/`parent_model`. The `refs.source` is clearly redundant with the `source` column. Transfer services should be migrated to write to the `source` field instead.

### 2.4 Line refs.source (DUPLICATE)

Line-level refs also store source lineage:

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/services/order_to_invoice.py` | L140-148 | `_prepare_line_refs()` → `refs.source.order_line_id`, `refs.source.order_id` |
| `apps/transactions/services/proposal_to_order.py` | L196 | `refs={"source": {"proposal_line_id": pl.id}}` |
| `apps/transactions/services/proposal_to_purchase.py` | L42 | `refs={"source": {"proposal_line_id": pl.id}}` |
| `apps/transactions/services/invoice_to_purchase.py` | L43 | `refs={"source": {"invoice_line_id": il.pk}}` |
| `apps/transactions/services/purchase_to_invoice.py` | L43 | `refs={"source": {"purchase_order_line_id": pl.pk}}` |
| `apps/transactions/services/purchase_to_order.py` | L43 | `refs={"source": {"purchase_order_line_id": pl.pk}}` |
| `apps/transactions/services/purchase_to_proposal.py` | L42 | `refs={"source": {"purchase_order_line_id": pl.pk}}` |

**Analysis:** Lines also duplicate source tracking. The base line model has an `item` JSONField but no dedicated `source` column for lineage. These could be moved to a line-level `source` column once one is added, but currently `refs.source` is the *de facto* storage. See Section 3 for verdict.

### 2.5 Contact Links Denormalization (PARTIAL DUPLICATE)

**FK exists:** Various models have `contact` FK → `core.Contact`  
**refs also stores:** `refs.links.contact` — list of contact objects with denormalized fields

| File | Lines | Description |
|------|-------|-------------|
| `apps/core/views/save_view.py` | L1010-1034 | Reads `contact.refs.links` to build email/phone/domain buckets, then writes back |
| `apps/core/views/save_view.py` | L1948-1967 | Same pattern in second save path |
| `apps/core/views/wcapi.py` | L543-551 | Reads `refs.links.email` to detect denorm email links |
| `apps/core/services/wcapi.py` | L239-272 | Reads/writes `refs.links` for contact denormalization on save |
| `apps/transactions/services/email_notifications.py` | L37 | `contact.refs.get('links', {}).get('email', [])` — uses refs to find email IDs instead of a FK/M2M |
| `apps/core/management/commands/qqqBy20260115/assign_contact_links.py` | L53-134 | Backfill script that writes contact link IDs into `refs.links.contact` on related models |

**Analysis:** The `refs.links.contact` is an intentional denormalization — it enriches the contact FK with additional embedded data (email, phone, address). However, the FK `contact_id` is the authority; `refs.links.contact` is a cache. The `RefsMismatchLog` system exists precisely to detect when these diverge.

### 2.6 Payment → Order (DUPLICATE)

**FK path:** No direct `Payment.order` FK exists  
**refs stores:** `payment.refs['order_ids']` — list of order IDs

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/models/payment.py` | L199-204 | `add_order_ref()` appends to `refs['order_ids']` |
| `apps/transactions/tests/test_payment_models.py` | L111 | Assert `123 in payment.refs['order_ids']` |

**Analysis:** No FK exists from Payment to Order, so `refs['order_ids']` is the only tracking. But since `PaymentApplication` links Payment→Invoice and Invoice can be traced to Order, this is a **convenience denormalization**, not a duplicate. Still, it's worth noting as a potential source of stale data.

---

## 3. Files Where `.refs` Is the ONLY Way a Relationship Is Tracked (No FK Exists)

These are legitimate uses of `refs` for data that has no FK counterpart.

### 3.1 Transfer Lineage Metadata (`refs.source`, `refs.xfer`)

| Pattern | Files | Notes |
|---------|-------|-------|
| `refs.source.*_id` on **lines** (no `source` column on line models) | All `*_to_*` transfer services | Line models lack a `source` JSONField, so `refs.source` is the only record of which source line produced the target line |
| `refs.xfer` (snapshot of source line data at transfer time) | `proposal_to_order.py:197`, `proposal_to_purchase.py:43`, `invoice_to_purchase.py:43`, `purchase_to_*.py` services | Transfer payload array for audit/rollback — no FK equivalent |

### 3.2 Action Dependencies (`refs.parents`, `refs.depends_on`, `refs.links.children`)

| File | Lines | Description |
|------|-------|-------------|
| `common/models.py` | L320-328 | Default `refs["parents"]`, `refs["depends_on"]` |
| `apps/core/services/action_service.py` | L32-116 | `add_child_dependency()`, `add_parent_dependency()`, `remove_*_dependency()`, `get_*_dependencies()` — Gantt chart parent↔child links stored entirely in refs |
| `apps/core/models/action.py` | L284-286 | `refs.get('parents', [])` for resolving parent actions |
| `apps/transactions/views/actions.py` | L252-256, L330-334 | Reads/writes `refs['depends_on']` |

**No FK exists** for action dependencies. This is a many-to-many relationship stored in JSON.

### 3.3 Contact Links (Denormalized Communication Records)

| File | Lines | Description |
|------|-------|-------------|
| `apps/core/services/action_service.py` | L12-14, L27-29 | `refs['contact_links']` — timestamped contact interaction log on actions |
| `apps/transactions/services/email_notifications.py` | L37 | `contact.refs.get('links', {}).get('email', [])` — email IDs for a contact |
| `apps/transactions/management/commands/populate_project_contacts.py` | L2-4 | `project.refs.links.contact` — denormalized list of active contact IDs |

**No M2M FK table** exists for contact↔email, contact↔phone, contact↔domain, contact↔location. These many-to-many relationships are tracked in `refs.links` buckets (email IDs, phone IDs, etc.).

### 3.4 Serial Reservations (`refs.serials`)

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/services/flow.py` | L111-113 | `refs['serials'] = []` — serial number reservation scaffold |

**No FK exists.** Serial tracking is stored in JSON on the line.

### 3.5 Linkage Chain (`refs.links.linkage`)

| File | Lines | Description |
|------|-------|-------------|
| `apps/transactions/views/order_views.py` | L90-96, L172-178 | Reads/writes `refs.links.linkage` — cross-transaction line chain IDs |
| `apps/transactions/views/linkage_views.py` | L51-53 | Reads `refs.links.linkage` |
| `apps/transactions/views/unified.py` | L302-304 | Reads `refs.links.linkage` |
| `apps/transactions/services/flow.py` | L116-124 | Propagates `refs.links.linkage` from source to destination |

**No FK exists.** The `LinkageEntry` model may exist but the cross-transaction thread is primarily JSON-based.

### 3.6 Keywords & Tags (`refs.keywords`, `refs.tags`)

| File | Lines | Description |
|------|-------|-------------|
| `apps/core/models/contact.py` | L321-333 | Contact keyword rebuilding into `refs['keywords']` |
| `apps/core/models/action.py` | L170-181 | Action keyword rebuilding |
| `apps/core/services/keywords.py` | L136-190 | Keyword generation service reading `refs` |
| `apps/core/management/commands/update_keywords.py` | L107-157 | Batch keyword update |

**No FK exists.** This is a denormalized full-text search accelerator.

### 3.7 Ledger → Org via refs (Queried, no FK on Ledger)

| File | Lines | Description |
|------|-------|-------------|
| `apps/accounts/services/ledger_balance.py` | L129 | `refs__links__org__id=org_id` — uses PostgreSQL JSON containment to query ledgers by org |
| `apps/accounts/services/ledger_balance.py` | L460, L567 | Same pattern repeated |

**Analysis:** No direct `Ledger.org` FK exists. The code queries via `refs__links__org__id` as primary path, with fallback to `invoice__org_id`. This is a candidate for adding an `org` FK to Ledger.

---

## 4. Inconsistencies & Issues Found

### Issue 1: Payment.refs is Fully Redundant with PaymentApplication

**Severity:** HIGH  
**Problem:** `Payment.refs['invoice_ids']` duplicates the `PaymentApplication` junction table. The `add_invoice_ref()` method writes to refs while `apply_payment_to_invoice()` creates `PaymentApplication` records. Views read from refs instead of the join table.  
**Fix:** Deprecate `refs['invoice_ids']` and `refs['order_ids']`. Have `payment_views.py:311` query `PaymentApplication.objects.filter(payment=payment)` instead.

### Issue 2: Transfer Services Write Lineage to Both `refs.source` and `source` Field

**Severity:** MEDIUM  
**Problem:** The base model now has a `source = models.JSONField(...)` column (`base_transaction_model.py:183`), but all 7 transfer services (`order_to_invoice`, `order_to_purchase`, etc.) still write lineage to `refs.source` instead. This means the dedicated `source` column is likely empty for transferred transactions while `refs.source` holds the data.  
**Fix:** Transfer services should write to the `source` column. Then migrate existing `refs.source` data to `source` and drop `refs.source`.

### Issue 3: `inventory_flow.py` Reads `refs.source` — Fragile Lineage Lookup

**Severity:** MEDIUM  
**Problem:** `_get_order_id_from_invoice_line()` (L245-247) and `_get_order_line_ids_from_invoice_line()` (L252-256) extract `order_id` and `order_line_id` from `refs.source`. If refs are pruned by the nightly task or manually cleared, inventory flow breaks silently.  
**Fix:** Once lineage moves to the `source` column, update these reads accordingly.

### Issue 4: `test_invoice_models.py` Puts Relationship Data Directly in refs

**Severity:** LOW  
**Problem:** Test at L33-40 creates an invoice with `refs={"order_id": 123}` and asserts `invoice.refs["order_id"] == 123`. This tests a legacy pattern of storing a relationship ID at the top level of refs (not even inside `refs.source`).  
**Fix:** Update test to reflect the new pattern (use `source` field or `refs.source`).

### Issue 5: Dual Contact Denormalization Codepaths

**Severity:** LOW  
**Problem:** Both `save_view.py` and `wcapi.py` have large blocks (L1010-1034 and L239-272 respectively) that copy/paste the same contact denormalization logic for refs. These are parallel endpoints that evolved independently.  
**Fix:** Extract shared logic into a single helper (partially done via `common/refs/contact_refs.py` but not fully adopted).

### Issue 6: `RefsMismatchLog` Exists but No Automated Reconciliation

**Severity:** INFO  
**Problem:** The mismatch log captures FK↔refs divergences reported by the React front-end, but there's no automated job to reconcile or fix mismatches. The nightly prune (`nightly_prune_refs`) removes stale links but doesn't compare against FK truth.  
**Recommendation:** Add a nightly reconciliation job that reads `RefsMismatchLog` entries and auto-heals refs.links from FK truth.

### Issue 7: `ledger_balance.py` Uses refs as Primary Query Path

**Severity:** MEDIUM  
**Problem:** Three queries in `ledger_balance.py` use `refs__links__org__id` as their primary filter (L129, L460, L567). If `refs.links.org` is ever pruned or not populated, ledger balance lookups fail.  
**Fix:** Add `org` FK to Ledger model, backfill from refs data, then query via FK.

---

## 5. Summary Matrix

| Category | Count | Action |
|----------|-------|--------|
| **refs duplicating FKs** (Payment.invoice_ids, source lineage) | 8+ files | Migrate to FK/dedicated columns |
| **refs as only relationship source** (no FK) | 15+ files | Keep for now; evaluate FK migration case-by-case |
| **refs for non-relationship data** (keywords, tags, serials, xfer) | 10+ files | Keep — appropriate use of JSON |
| **Denormalization caches** (contact links, linkage) | 8+ files | Keep with RefsMismatchLog monitoring |
| **Inconsistencies requiring cleanup** | 7 issues | See Section 4 |

### Priority Actions

1. **Payment refs cleanup** — Remove `refs['invoice_ids']` / `refs['order_ids']`, use `PaymentApplication` table
2. **Transfer lineage** — Move `refs.source.*_id` writes to the `source` JSONField column on TransactionBaseModel
3. **Inventory flow reads** — Update to read from `source` column once transfer lineage is migrated
4. **Ledger org FK** — Add `org` FK to Ledger, remove reliance on `refs__links__org__id`
5. **Test updates** — Fix `test_invoice_models.py` and `test_payment_*.py` to reflect new patterns
