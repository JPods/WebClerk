# FK Naming Conventions


<!-- TOC START -->

## Table of Contents

- [FK Naming Conventions](#fk-naming-conventions)
  - [Table of Contents](#table-of-contents)
  - [Rule](#rule)
  - [Why This Matters](#why-this-matters)
  - [The Three Patterns (and Which to Use)](#the-three-patterns-and-which-to-use)
    - [Pattern A — field = model name (STANDARD)](#pattern-a--field--model-name-standard)
    - [Pattern B — field has \_id suffix (AVOID)](#pattern-b--field-has-_id-suffix-avoid)
    - [Pattern C — field has \_fk suffix (DISAMBIGUATION ONLY)](#pattern-c--field-has-_fk-suffix-disambiguation-only)
  - [Parent–Child Relationships](#parentchild-relationships)
  - [db\_column Override Rule](#db_column-override-rule)
  - [Current Inventory — Fields to Rename](#current-inventory--fields-to-rename)
    - [Pattern B Fields (48) — need rename + db\_column](#pattern-b-fields-48--need-rename--db_column)
    - [Pattern C Fields (3) — acceptable, keep as-is](#pattern-c-fields-3--acceptable-keep-as-is)
    - [IntegerField → FK Candidates (8 definite)](#integerfield--fk-candidates-8-definite)
  - [Migration Approach](#migration-approach)
  - [Related Documentation](#related-documentation)

<!-- TOC END -->

Date: 2026-02-15
Review: —
Status: Active
Owner: Bill

## Rule

**Name every ForeignKey field after the model it points to** (or a
descriptive role name), **never with an `_id` suffix**. Django
automatically creates a `<field>_id` attribute for the raw integer value.
If you name the field `customer_id`, Django creates `customer_id_id` —
confusing in Python and in the database.

When an existing non-FK field already occupies the natural name, use the
`_fk` suffix with an explicit `db_column` override. This is the only
acceptable deviation.

## Why This Matters

| You write | Python gives you | DB column (no `db_column`) |
|---|---|---|
| `customer = FK(...)` | `obj.customer` (instance) / `obj.customer_id` (int) | `customer_id` ✅ |
| `customer_id = FK(...)` | `obj.customer_id` (instance) / `obj.customer_id_id` (int) | `customer_id_id` ❌ |

The `_id` suffix pattern:
- Creates ugly `_id_id` columns in Postgres unless you add a `db_column`
  override to every single one.
- Makes code ambiguous: `obj.customer_id` returns the ORM object, not an
  integer, which surprises every Django developer.
- Breaks Django conventions for `raw_id_fields`, `autocomplete_fields`,
  admin, and DRF serializers that all expect the bare model name.

## The Three Patterns (and Which to Use)

### Pattern A — field = model name (STANDARD)

```python
# ✅ Always use this
customer = models.ForeignKey(
    'orgs.OrgBase', on_delete=models.SET_NULL,
    blank=True, null=True,
    db_column='customer_id',        # preserves existing DB column
    related_name='orders_as_customer',
)
# Python: order.customer    → OrgBase instance
# Python: order.customer_id → raw int (auto-created by Django)
# DB col: customer_id
```

### Pattern B — field has \_id suffix (AVOID)

```python
# ❌ Never do this
warehouse_id = models.ForeignKey(
    'products.Warehouse', on_delete=models.SET_NULL,
    blank=True, null=True,
)
# Python: obj.warehouse_id    → Warehouse instance (misleading!)
# Python: obj.warehouse_id_id → raw int (ugly)
# DB col: warehouse_id_id     (double suffix)
```

**This is the most common problem in our codebase (48 fields).**

### Pattern C — field has \_fk suffix (DISAMBIGUATION ONLY)

Use only when a non-FK field already occupies the natural name:

```python
# ✅ Acceptable when CharField "terms" already exists
terms = models.CharField(max_length=30, blank=True, null=True)
terms_fk = models.ForeignKey(
    'transactions.PaymentTerm', on_delete=models.SET_NULL,
    blank=True, null=True,
    db_column='terms_id',           # clean DB column
    related_name='orgs_with_terms',
)
# Python: obj.terms      → str (legacy)
# Python: obj.terms_fk   → PaymentTerm instance
# Python: obj.terms_fk_id → raw int (acceptable)
# DB col: terms_id
```

**We have 3 fields using this pattern — all correctly have `db_column` overrides.**

## Parent–Child Relationships

For line-item → header (parent) relationships, name the FK after the
parent model, not `parent_id`:

```python
# ✅ Correct: name = parent model
class OrderLine(BaseLineCore):
    order = models.ForeignKey(
        'transactions.Order', on_delete=models.CASCADE,
        related_name='lines',
    )
    # line.order    → Order instance
    # line.order_id → raw int

# ✅ Correct: descriptive role when the relationship is not 1:1 with a model
class BillOfMaterial(BaseModel):
    parent_item = models.ForeignKey(
        'products.Item', on_delete=models.CASCADE,
        related_name='bom_as_parent',
    )
    child_item = models.ForeignKey(
        'products.Item', on_delete=models.CASCADE,
        related_name='bom_as_child',
    )

# ❌ Wrong
class InvoiceLine(BaseLineCore):
    invoice_id = models.ForeignKey(        # creates invoice_id_id
        'transactions.Invoice', ...
    )
```

For self-referential parent relationships, `parent` is acceptable:

```python
parent = models.ForeignKey(
    'self', on_delete=models.SET_NULL,
    blank=True, null=True,
    db_column='parent_id',
    related_name='children',
)
```

## db\_column Override Rule

Always provide `db_column` when:
1. The field is being **renamed** from Pattern B → Pattern A (preserves
   existing DB column, avoids migration).
2. The natural Django column name would conflict with an existing column.
3. The DB column follows a legacy naming scheme you want to preserve.

When creating a **brand-new** FK on a new model, you can omit `db_column`
and let Django use its default (`<field>_id`), which is correct under
Pattern A.

## Current Inventory — Fields to Rename

### Pattern B Fields (48) — need rename + db\_column

These FK fields use `_id` suffix and most lack `db_column` (creating
`_id_id` in the database). Rename to Pattern A with a `db_column`
override.

**OrgBase** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `contact_id = FK(Contact)` | `contact` | `contact_id` (already set) |

**Ledger** (3 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `invoice_id = FK(Invoice)` | `invoice` | `invoice_id` |
| `term_id = FK(Term)` | `term` | `term_id` |
| `gl_account_id = FK(Gl_account)` | `gl_account` | `gl_account_id` |

**Action** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `action_id = FK(self)` | `parent_action` | `action_id` |

**AuditLog** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `user_id = FK(User)` | `user` | `user_id` |

**APILog** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `user_id = FK(User)` | `user` | `user_id` |

**SoftDeleteLedger** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `contenttype_id = FK(ContentType)` | `content_type` | `contenttype_id` |

**QuestionAnswer** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `setting_id = FK(Setting)` | `setting` | `setting_id` |

**Catalog** (6 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `orgbase_id = FK(OrgBase)` | `orgbase` | `orgbase_id` |
| `customer_orgbase_id = FK(OrgBase)` | `customer_orgbase` | `customer_orgbase_id` |
| `manufacturer_orgbase_id = FK(OrgBase)` | `manufacturer_orgbase` | `manufacturer_orgbase_id` |
| `rep_orgbase_id = FK(OrgBase)` | `rep_orgbase` | `rep_orgbase_id` |
| `employee_orgbase_id = FK(OrgBase)` | `employee_orgbase` | `employee_orgbase_id` |
| `connection_id = FK(Connection)` | `connection` | `connection_id` |

**CatalogLine** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `catalog_id = FK(Catalog)` | `catalog` | `catalog_id` |

**DeliveryVisit** (3 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `orgbase_id = FK(OrgBase)` | `orgbase` | `orgbase_id` |
| `customer_orgbase_id = FK(OrgBase)` | `customer_orgbase` | `customer_orgbase_id` |
| `catalog_id = FK(Catalog)` | `catalog` | `catalog_id` |

**DeliveryLine** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `deliveryvisit_id = FK(DeliveryVisit)` | `delivery_visit` | `deliveryvisit_id` |
| `orgitem_id = FK(OrgItem)` | `orgitem` | `orgitem_id` |

**InventoryCheck** (3 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `orgbase_id = FK(OrgBase)` | `orgbase` | `orgbase_id` |
| `catalog_id = FK(Catalog)` | `catalog` | `catalog_id` |
| `user_id = FK(User)` | `user` | `user_id` |

**InventoryCheckLine** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `inventorycheck_id = FK(InventoryCheck)` | `inventory_check` | `inventorycheck_id` |
| `orgitem_id = FK(OrgItem)` | `orgitem` | `orgitem_id` |

**InventoryLayer** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `warehouse_id = FK(Warehouse)` | `warehouse` | `warehouse_id` |

**InventoryMovement** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `warehouse_id = FK(Warehouse)` | `warehouse` | `warehouse_id` |
| `inventorylayer_id = FK(InventoryLayer)` | `inventory_layer` | `inventorylayer_id` |

**PendingInventoryAdjustment** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `inventorylayer_id = FK(InventoryLayer)` | `inventory_layer` | `inventorylayer_id` |

**InventoryReservation** (3 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `item_id = FK(Item)` | `item` | `item_id` |
| `warehouse_id = FK(Warehouse)` | `warehouse` | `warehouse_id` |
| `inventorylayer_id = FK(InventoryLayer)` | `inventory_layer` | `inventorylayer_id` |

**ItemLinkedBase** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `item_id = FK(Item)` | `item` | `item_id` |

**OrgItem** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `orgbase_id = FK(OrgBase)` | `orgbase` | `orgbase_id` |
| `catalog_id = FK(Catalog)` | `catalog` | `catalog_id` |

**BillOfMaterial** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `parent_id = FK(Item)` | `parent_item` | `parent_id` |
| `child_id = FK(Item)` | `child_item` | `child_id` |

**Serial** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `inventorylayer_id = FK(InventoryLayer)` | `inventory_layer` | `inventorylayer_id` |

**SerialLog** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `serial_id = FK(Serial)` | `serial` | `serial_id` |

**Bundle** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `connection_id = FK(Connection)` | `connection` | `connection_id` |

**Payment** (4 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `invoice_id = FK(Invoice)` | `invoice` | `invoice_id` |
| `contact_id = FK(Contact)` | `contact` | `contact_id` |
| `paymentmethod_id = FK(PaymentMethod)` | `payment_method` | `paymentmethod_id` |
| `paymentterm_id = FK(PaymentTerm)` | `payment_term` | `paymentterm_id` |

**PaymentApplication** (2 fields):

| Current | Rename to | `db_column` |
|---|---|---|
| `payment_id = FK(Payment)` | `payment` | `payment_id` |
| `invoice_id = FK(Invoice)` | `invoice` | `invoice_id` |

**ProjectAssociation** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `project_id = FK(Project)` | `project` | `project_id` |

**RequisitionLine** (1 field):

| Current | Rename to | `db_column` |
|---|---|---|
| `requisition_id = FK(Requisition)` | `requisition` | `requisition_id` |

### Pattern C Fields (3) — acceptable, keep as-is

| Model | Field | `db_column` | Reason |
|---|---|---|---|
| `OrgBase` | `terms_fk` | `terms_id` | `terms` CharField exists |
| `TransactionBaseModel` | `terms_fk` | `terms_id` | `terms` CharField exists |
| `BaseLineCore` | `item_fk` | `item_id_fk` | `item_id` IntegerField exists |

### IntegerField → FK Candidates (8 definite)

These should become proper ForeignKey fields (Pattern A), converting from
plain integer columns:

| Model | Field | Type | Target Model |
|---|---|---|---|
| `OrgBase` | `address_id` | `IntegerField` | `Address` |
| `OrgBase` | `email_id` | `IntegerField` | `Email` |
| `OrgBase` | `phone_id` | `IntegerField` | `Phone` |
| `OrgBase` | `domain_id` | `IntegerField` | `Domain` |
| `Contact` | `email_id` | `BigIntegerField` | `Email` |
| `Contact` | `address_id` | `BigIntegerField` | `Address` |
| `Contact` | `phone_id` | `BigIntegerField` | `Phone` |
| `Contact` | `domain_id` | `BigIntegerField` | `Domain` |

When converted, name them `email`, `address`, `phone`, `domain` with
`db_column` preserving the existing `_id` column names.

## Migration Approach

Renaming a ForeignKey field in Python **does not require a database
migration** when `db_column` is set to the existing column name. Django
only tracks the DB column; the Python attribute is ORM-only.

Steps per field:
1. Rename the field (e.g., `warehouse_id` → `warehouse`).
2. Add `db_column='warehouse_id'` if not already present.
3. Update all Python references: model code, admin, serializers, views,
   management commands, tests.
4. Run `makemigrations` — Django generates a `RenameField` or
   `AlterField`; confirm `db_column` is unchanged.
5. Run `migrate` — no-op at DB level.

Work in batches by app to keep diffs reviewable:
1. `apps/orgs` (1 field: `contact_id` → `contact`)
2. `apps/core` (3 fields: `action_id`, `user_id` × 2)
3. `apps/products` (20+ fields)
4. `apps/transactions` (10+ fields)
5. `apps/accounts` (4 fields)
6. `apps/docs`, `apps/sync` (3 fields)

## Related Documentation

- [FK-First Migration Policy](fk-first-migration.md) — when to use FK vs
  `.refs`
- [Model Name Conventions](model_name_conventions.md) — endpoint & table
  naming
- [Data Model Overview](webclerk3_data_models.md) — full schema reference
