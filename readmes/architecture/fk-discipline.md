# FK Discipline — Complete Reference

**Scar origin:** Touch.contact used CASCADE — deleting a contact deleted all
touch history. Extended audit found CASCADE on all communication models.
All converted to values (BigIntegerField) on 2026-08-27.

## The Rule

| Pattern | When to use | on_delete |
|---------|-------------|-----------|
| **FK CASCADE** | Child has no meaning without parent (line→header) | CASCADE |
| **FK PROTECT** | Prevent deletion while references exist (warehouse, BOM component) | PROTECT |
| **FK SET_NULL** | Both independent, but Django ORM benefits needed | SET_NULL |
| **BigIntegerField** | Both independent, no ORM traversal needed | — (no cascade) |

**Default for new fields:** BigIntegerField. Use FK only with explicit justification.

## Complete Field Inventory

### Correct CASCADE (structural — child dies with parent)

| Model | Field | Target | Why CASCADE is correct |
|-------|-------|--------|----------------------|
| InvoiceLine.invoice | Invoice | Line is part of invoice |
| OrderLine.order | Order | Line is part of order |
| ProposalLine.proposal | Proposal | Line is part of proposal |
| PurchaseLine.purchase | Purchase | Line is part of purchase |
| WorkOrderLine.workorder | WorkOrder | Line is part of workorder |
| RequisitionLine.requisition | Requisition | Line is part of requisition |
| ReceiptLine.receipt | Receipt | Line is part of receipt |
| Payment.invoice | Invoice | Payment applies to specific invoice |
| Payment.purchase | Purchase | Payment applies to specific purchase |
| PaymentApplication.payment | Payment | Application is part of payment |
| PaymentApplication.invoice | Invoice | Application targets specific invoice |
| PendingPaymentApplication.* | Payment/Invoice | Same as PaymentApplication |
| ProjectAssociation.project | Project | Junction record IS the relationship |
| UserDailyLog.user | AUTH_USER | Log belongs to user session |
| UserProfile.user | AUTH_USER | Profile IS the user extension |
| Action.parent_action | Action | Child action depends on parent |
| Bundle.connection | Connection | Bundle belongs to connection |
| SerialLog.serial | Serial | Log entry belongs to serial |
| CatalogLine.catalog | Catalog | Line is part of catalog |
| BillOfMaterial.parent_item | Item | BOM belongs to parent item |
| Variant.item | Item | Variant IS the item |
| Variant.parent_item | Item | Variant derives from parent |
| OrgItem.orgbase | OrgBase | Pricing record belongs to org |
| DeliveryVisit.orgbase | OrgBase | Visit belongs to org |
| DeliveryLine.delivery_visit | DeliveryVisit | Line is part of visit |
| DeliveryLine.orgitem | OrgItem | Line references org pricing |
| InventoryCheckLine.* | InventoryCheck/OrgItem | Line is part of check |
| InventoryReservation.item | Item | Reservation is for specific item |
| Conversation.user | AUTH_USER | Chat belongs to user |
| Message.conversation | Conversation | Message is part of conversation |
| SchemaDrift.git_event | GitEvent | Drift detected in specific event |
| SourceFile.project | ConversionProject | File belongs to project |
| ColumnMap.source_file | SourceFile | Map belongs to file |
| StagingRow.source_file | SourceFile | Row belongs to file |
| PassLog.project | ConversionProject | Log belongs to project |
| Oddity.project | ConversionProject | Oddity belongs to project |

### Correct PROTECT (prevent deletion while references exist)

| Model | Field | Target | Why PROTECT is correct |
|-------|-------|--------|----------------------|
| BaseLineCore.item_fk | Item | Can't delete item while on a transaction |
| InventoryLayer.warehouse | Warehouse | Can't delete warehouse with inventory |
| InventoryMovement.warehouse | Warehouse | Can't delete warehouse with history |
| InventoryReservation.warehouse | Warehouse | Can't delete warehouse with holds |
| ReceiptLine.warehouse | Warehouse | Can't delete warehouse with receipts |
| BillOfMaterial.child_item | Item | Can't delete component while in a BOM |

### Correct SET_NULL (independent lifecycle, ORM benefits)

| Model | Field | Target | Notes |
|-------|-------|--------|-------|
| TransactionBaseModel.customer | OrgBase | Transaction survives customer deactivation |
| TransactionBaseModel.vendor | OrgBase | Transaction survives vendor deactivation |
| TransactionBaseModel.manufacturer | OrgBase | Same |
| TransactionBaseModel.contact | Contact | Same |
| TransactionBaseModel.terms_fk | PaymentTerm | Terms can change |
| Contact.employee/customer/vendor/manufacturer/rep | OrgBase | Contact survives org deactivation |
| OrgBase.terms_fk | PaymentTerm | Terms can change |
| OrgBase.tax_jurisdiction | TaxJurisdiction | Jurisdiction can change |
| Item.vendor/manufacturer | OrgBase | Item survives org deactivation |
| Catalog.orgbase/customer_orgbase/etc. | OrgBase | Catalog survives org deactivation |
| Catalog.connection | Connection | Catalog survives connection removal |
| Receipt.purchase/workorder | Purchase/WorkOrder | Receipt survives source deactivation |
| ReceiptLine.purchase_line/workorder_line | *Line | Receipt survives source line removal |
| ReceiptLine.inventory_layer | InventoryLayer | Receipt survives layer depletion |
| InventoryMovement.inventory_layer | InventoryLayer | Movement history survives |
| InventoryReservation.inventory_layer | InventoryLayer | Reservation survives |
| Serial.inventory_layer | InventoryLayer | Serial survives layer depletion |
| OrgItem.catalog | Catalog | Pricing survives catalog removal |
| Ledger.org/invoice/term/gl_account | Various | Ledger survives reference changes |
| Erosion.org/contact | OrgBase/Contact | Erosion record survives |
| JournalBatch.run_by | Contact | Batch survives contact changes |
| AuditLog.user / APILog.user | Contact | Log survives user changes |
| UserProfile.contact | Contact | Profile survives contact changes |
| QuestionAnswer.document | Document | QA survives document changes |
| AliceObservation.contact/acknowledged_by | Contact | Observation survives |

### Correct BigIntegerField (value — no cascade, no ORM traversal)

| Model | Field | Target | Notes |
|-------|-------|--------|-------|
| Action.contact_id | Contact | Independent lifecycle |
| Action.project_id | Project | Independent lifecycle |
| Touch.contact_id | Contact | Historical record survives deletion |
| Touch.action_id | Action | Touch survives action deletion |
| Touch.org_id | OrgBase | Paired with org_model discriminator |
| OrgBase.contact_id | Contact | Primary-among-many pointer |
| Address.contact_id | Contact | Communication survives contact deletion |
| Phone.contact_id | Contact | Same |
| Email.contact_id | Contact | Same |
| Domain.contact_id | Contact | Same |
| Contact.email_id/address_id/phone_id/domain_id | Various | PJPV pointers to primary comm |
| OrgBase.address_id/email_id/phone_id/domain_id | Various | PJPV pointers to primary comm |
| Setting.org_id/contact_id | OrgBase/Contact | Scope pointers |
| Project.contact_id | Contact | Project owner pointer |
| TransactionBaseModel.parent_id | Polymorphic | Source document reference |
| Payment.parent_id | Polymorphic | Source document |
| GlJournal.source_id | Polymorphic | Paired with source_model |
| Erosion.source_id/parent_id | Polymorphic | Paired with discriminator |
| InventoryLayer.source_doc_id | Polymorphic | Source receipt/PO |
| InventoryMovement.source_doc_id | Polymorphic | Source transaction |
| ItemXRef.source_id | Polymorphic | External system reference |
| ProjectAssociation.object_id | Polymorphic | Paired with model_code |
| StatementLine.payment_id | Payment | Loose reference |
| LinkageEntry.group_id/record_id | Polymorphic | Linkage group system |
| Tag.record_id | Polymorphic | Paired with model_name |
| QuestionAnswer.parent_id | Polymorphic | Paired with parent_model |

### REVIEW NEEDED — FKs that may be wrong

| Model | Field | Current | Concern |
|-------|-------|---------|---------|
| Contact.employee/customer/vendor/manufacturer/rep | FK SET_NULL | These are the WC2 value pattern. Bill used BigInt in WC2. Consider converting — but SET_NULL is safe (no data loss) |

*Resolved 2026-08-28:* Payment.contact → now FK SET_NULL. AliceCoachingLog.contact, AliceInsight.contact → now BigIntegerField. DeliveryVisit.customer_orgbase → now BigIntegerField (customer_orgbase_id).

## Alice Orphan Watch

With values replacing FKs, orphan records can accumulate. Alice runs a weekly scan:

1. Find communication records (Email, Phone, Address, Domain) where `contact_id` points to a deleted/inactive Contact
2. Find Touch records where `contact_id` or `action_id` points to deleted records
3. Mark orphans for deletion
4. Supervisor has 30 days to save them
5. Report: count per model, record IDs, suggested action

---

## Naming Conventions

**Date:** 2026-02-15

### The Rule

**Name every ForeignKey field after the model it points to** (or a descriptive role
name), **never with an `_id` suffix**. Django automatically creates a `<field>_id`
attribute for the raw integer value. If you name the field `customer_id`, Django
creates `customer_id_id`.

### The Three Patterns

**Pattern A — field = model name (STANDARD):**
```python
customer = models.ForeignKey(
    'orgs.OrgBase', on_delete=models.SET_NULL,
    blank=True, null=True,
    db_column='customer_id',
    related_name='orders_as_customer',
)
# Python: order.customer -> OrgBase instance
# Python: order.customer_id -> raw int (auto-created)
# DB col: customer_id
```

**Pattern B — field has _id suffix (AVOID):**
```python
# Creates warehouse_id_id in the database. 48 fields have this problem.
warehouse_id = models.ForeignKey('products.Warehouse', ...)
```

**Pattern C — field has _fk suffix (DISAMBIGUATION ONLY):**
Use only when a non-FK field already occupies the natural name:
```python
terms = models.CharField(max_length=30, blank=True, null=True)
terms_fk = models.ForeignKey(
    'transactions.PaymentTerm', on_delete=models.SET_NULL,
    db_column='terms_id',
    related_name='orgs_with_terms',
)
```
3 fields use this pattern — all correctly have `db_column` overrides.

### Parent-Child Relationships

Name the FK after the parent model, not `parent_id`:
```python
class OrderLine(BaseLineCore):
    order = models.ForeignKey('transactions.Order', on_delete=models.CASCADE, related_name='lines')
```

For self-referential, `parent` is acceptable with `db_column='parent_id'`.

### db_column Override Rule

Always provide `db_column` when: renaming Pattern B -> A, natural column would conflict,
or preserving legacy column names. Brand-new FKs on new models can omit it.

### Rename Inventory (48 Pattern B Fields)

These FK fields use `_id` suffix and most lack `db_column`. Rename to Pattern A with
`db_column` override. Full inventory by model:

| App | Models | Field count |
|-----|--------|-------------|
| `apps/orgs` | OrgBase | 1 |
| `apps/core` | Action, AuditLog, APILog, SoftDeleteLedger, QuestionAnswer | 5 |
| `apps/products` | Catalog(6), CatalogLine, DeliveryVisit(3), DeliveryLine(2), InventoryCheck(3), InventoryCheckLine(2), InventoryLayer, InventoryMovement(2), PendingInventoryAdjustment, InventoryReservation(3), ItemLinkedBase, OrgItem(2), BillOfMaterial(2), Serial, SerialLog | 30 |
| `apps/transactions` | Payment(4), PaymentApplication(2), ProjectAssociation, RequisitionLine, Bundle | 9 |

### Migration Approach

Renaming a ForeignKey field in Python **does not require a database migration** when
`db_column` is set to the existing column name. Work in batches by app to keep diffs
reviewable.

---

## FK-First Migration Status

**Policy:** Use proper Django `ForeignKey` for all entity references. `.refs` JSON is
set aside during active development. Never read from or write to `.refs` for any
relationship that already has an FK. New relationships must be ForeignKey fields.

Once core development stabilises, `.refs` will be re-evaluated as an optional
denormalized read cache maintained by Celery.

### Completed (FK is Source of Truth)

Transaction headers -> Orgs/Contact/Terms, transaction lines -> headers/items,
Org -> Contact/Terms, Contact -> Org roles, Communications -> Contact, Payment,
PaymentApplication, Receipt/ReceiptLine, Inventory (Layer/Movement/Reservation),
Serial/SerialLog, Catalog/CatalogLine, Delivery, InventoryCheck, BOM, Variants,
Ledger, ProjectLink, RequisitionLine, Bundle, QA, Audit logs.

### Deferred (Still Refs-Only)

| Relationship | Why Deferred |
|-------------|--------------|
| Action -> targets (transactions, products, docs, comms) | Polymorphic — needs GenericFK or join table |
| Payment -> multiple invoices | M2M — single FK exists; multi-invoice is future M2M table |
| Invoice/Order source tracking | Design TBD for order-to-invoice lineage |
| Warehouse -> Items | Through-table via InventoryLayer may suffice |
| Project -> Contacts | Low priority; ProjectLink partially covers |
| Contact <-> Comms bidirectional | FK exists on comms side; reverse query sufficient |
| Item variant scaffolding | Variant FK model exists; refs redundant |
| Party role snapshots (BillTo/ShipTo) | Denormalized print cache — not a relationship |

### Development Guidelines

1. New relationships: always FK or M2M. Never new `.refs.links` buckets.
2. Reading: use FK joins / `select_related` / `prefetch_related`.
3. Writing: save via FK fields. Don't update `refs.links` for FK-migrated relationships.
4. Serializers: return FK-based IDs. Omit `refs` unless needed for keywords/tags.
5. RefsMismatchLog: keep operational for FK-vs-refs divergence tracking.

### Infrastructure

| Component | Path |
|-----------|------|
| RefsMixin | `common/mixins/refs_mixin.py` |
| PolicyEngine | `common/refs/policy.py` |
| Refs link helpers | `common/refs/links.py` |
| Celery tasks | `common/refs/tasks.py` |
| RefsMismatchLog | `apps/core/models/refs_mismatch_log.py` |
| FK naming audit | `audit_foreign_keys.py` (project root) |
