# FK-First Migration — Status & Development Policy


<!-- TOC START -->

## Table of Contents

- [FK-First Migration — Status & Development Policy](#fk-first-migration--status--development-policy)
  - [Table of Contents](#table-of-contents)
  - [Policy](#policy)
  - [Background](#background)
  - [Migration Status](#migration-status)
    - [Completed — FK is Source of Truth](#completed--fk-is-source-of-truth)
    - [Deferred — Still Refs-Only](#deferred--still-refs-only)
  - [Development Guidelines](#development-guidelines)
  - [Infrastructure](#infrastructure)
  - [Related Documentation](#related-documentation)

<!-- TOC END -->

Date: 2026-02-15
Review: —
Status: Active
Owner: Bill

## Policy

**FK-first**: use proper Django `ForeignKey` for all entity references.
`.refs` JSON is set aside during active development. Do not read from or
write to `.refs` for any relationship that already has an FK. New
relationships must be implemented as ForeignKey fields; do not introduce
new `.refs.links` buckets.

Once core development stabilises, `.refs` will be re-evaluated as an
optional denormalized read cache maintained by Celery — it is **never**
the source of truth for any FK-migrated relationship.

## Background

Every model inherits `RefsMixin` (via `BaseModel`), which provides a JSONB
`refs` column with a default shape:

```json
{
  "keywords": [],
  "tags": [],
  "links": { "contact": [], "item": [] },
  "parents": []
}
```

Early development used `refs.links` to store cross-entity relationships as
arrays of integer PKs inside this JSON blob. This was fast to iterate on
(no migrations for new link types) but introduced several problems:

- No referential integrity — orphan IDs accumulate silently.
- Reconcile/prune management commands needed to repair drift.
- Queries against JSON arrays are slower and harder to optimise than FK joins.
- Two sources of truth invite mismatches (tracked via `RefsMismatchLog`).

The project has now migrated the majority of relationships to proper
ForeignKey fields. The `refs` column and `RefsMixin` remain in the schema
but should be treated as inert during development.

## Migration Status

### Completed — FK is Source of Truth

| Domain | Models / Fields | Notes |
|--------|----------------|-------|
| **Transaction headers → Orgs** | `TransactionBaseModel.customer`, `.vendor`, `.manufacturer` → `OrgBase` | `db_column` preserves existing columns |
| **Transaction headers → Contact** | `TransactionBaseModel.contact` → `Contact` | |
| **Transaction headers → Terms** | `TransactionBaseModel.terms_fk` → `PaymentTerm` | |
| **Transaction lines → Headers** | `OrderLine.parent`, `InvoiceLine.parent`, etc. | All line models use FK `parent` |
| **Transaction lines → Items** | `BaseLineCore.item_fk` → `Item` | |
| **Org → Contact** | `OrgBase.contact` → `Contact` | Primary contact only |
| **Org → Terms** | `OrgBase.terms_fk` → `PaymentTerm` | |
| **Contact → Org roles** | `Contact.employee`, `.customer`, `.vendor`, `.manufacturer`, `.rep` → `OrgBase` | |
| **Communications → Contact** | `Email.contact`, `Phone.contact`, `Address.contact`, `Domain.contact` → `Contact` | Migration 0007 |
| **Payment** | `Payment.invoice_id`, `.contact_id`, `.paymentmethod_id`, `.paymentterm_id` | |
| **Payment application** | `PaymentApplication.payment_id`, `.invoice_id` | |
| **Receipt** | `Receipt.purchase`, `.workorder` | |
| **Receipt lines** | `ReceiptLine.receipt`, `.purchase_line`, `.workorder_line`, `.warehouse`, `.inventory_layer` | |
| **Inventory** | `InventoryLayer.warehouse_id`, `InventoryMovement`, `InventoryReservation`, `PendingAdjustment` | All FK |
| **Serial tracking** | `Serial.inventorylayer_id`, `SerialLog.serial_id` | |
| **Catalog** | `Catalog.orgbase_id` + 4 org-type FKs, `.connection_id` | |
| **Catalog lines** | `CatalogLine.catalog_id` | |
| **Delivery visits** | `DeliveryVisit`, `DeliveryVisitLine` — all FKs | |
| **Inventory checks** | `InventoryCheck`, `InventoryCheckLine` — all FKs | |
| **BOM** | `BillOfMaterial.parent_id`, `.child_id` → `Item` | |
| **Variants** | `Variant.parent_item` → `Item` | |
| **Ledger** | `Ledger.invoice_id`, `.term_id`, `.gl_account_id` | |
| **Project links** | `ProjectLink.project_id` | |
| **Requisition lines** | `RequisitionLine.requisition_id` | |
| **Bundles** | `Bundle.connection_id` | |
| **QA** | `QuestionAnswer.setting_id` | |
| **Support** | `TaskRun.task` → `ScheduledTask` | |
| **Audit** | `AuditLog.user_id`, `ApiLog.user_id` | |

### Deferred — Still Refs-Only

These remain in `.refs` and will be converted after core development
stabilises. **Do not add new code that reads/writes these paths** — work
with existing helpers if you must touch them.

| Relationship | Current Storage | Why Deferred |
|-------------|----------------|--------------|
| Action → targets (transactions, products, docs, comms) | `action.refs.links.*` | Polymorphic — needs GenericFK or dedicated join table design |
| Payment → multiple invoices | `payment.refs.invoice_ids`, `.order_ids` | M2M — single FK exists; multi-invoice is a future M2M table |
| Invoice/Order source tracking | `invoice.refs.source.order_id` | Design TBD for order-to-invoice lineage |
| Warehouse → Items | `warehouse.refs.links.items` | Through-table via `InventoryLayer` may suffice |
| Project → Contacts | `project.refs.links.contact` | Low priority; `ProjectLink` partially covers |
| Contact ↔ Comms bidirectional | `contact.refs.links.email`, etc. | FK exists on comms side; reverse query via FK is sufficient |
| Item variant scaffolding | `item.refs.variants` | `Variant` FK model exists; refs redundant |
| Party role snapshots (BillTo/ShipTo) | `refs.party_roles` | Denormalized print cache — not a relationship |

## Development Guidelines

1. **New relationships** — always use `ForeignKey` (or `ManyToManyField`).
   Never store a new PK array in `.refs.links`.

2. **Reading related data** — use FK joins / `select_related` /
   `prefetch_related`. Do not parse `refs.links` for any migrated relationship.

3. **Writing** — save via FK fields. Do not update `refs.links` on save
   for FK-migrated relationships.

4. **Serializers** — return FK-based IDs and nested representations.
   Omit `refs` from API responses unless explicitly needed for keywords/tags.

5. **Celery refs-sync tasks** — leave `common/refs/tasks.py` intact but
   do not wire new signals to it. Existing tasks may continue running for
   deferred relationships; they are harmless for FK-migrated ones.

6. **RefsMismatchLog** — keep operational. It validates that nothing is
   silently depending on stale refs data.

7. **Management commands** — `reconcile_links` and
   `assign_contact_links` are legacy. Do not call them for FK-migrated
   models. They remain available for the deferred relationships listed above.

8. **`RefsMixin` / `BaseModel`** — do not remove. The JSONB column stays
   in the schema; it simply goes unused for FK-migrated relationships.

## Infrastructure

| Component | Path | Purpose |
|-----------|------|---------|
| RefsMixin | `common/mixins/refs_mixin.py` | Provides `refs` JSONB field on all models |
| PolicyEngine | `common/refs/policy.py` | Rules for attach/prune (dormant for FK models) |
| Refs link helpers | `common/refs/links.py` | Bidirectional link management — legacy |
| Celery tasks | `common/refs/tasks.py` | Async refs sync — dormant for FK models |
| RefsMismatchLog | `apps/core/models/refs_mismatch_log.py` | Runtime FK-vs-refs divergence tracker |
| RefsMismatchView | `apps/core/views/refs_mismatch_view.py` | React front-end POSTs discrepancies here |
| audit_foreign_keys.py | project root | AST scanner for FK naming compliance |

## Related Documentation

- [relationships.md](relationships.md) — original link strategy (JSON-based)
- [refs_policies.md](refs_policies.md) — materialized graph index design
- [refs_setting.md](refs_setting.md) — keyword/refs configuration
- [model-fields.json](../model-fields.json) — field inventory

---
This document supersedes the refs-first approach in `relationships.md` for
all FK-migrated models. Update this file when new relationships are added
or deferred items are converted.
