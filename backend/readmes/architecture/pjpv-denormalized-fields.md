# PJPV Shadow Field Registry

**Established:** 2026-08-22
**Terminology updated:** 2026-08-23 — "shadow fields" is the standard term
**Updated:** 2026-08-24 — removed 13 deleted scalar columns (6 TransactionBaseModel,
4 OrgBase, 3 Contact); 7 shadow fields remain across 5 models
**Rule:** Shadow fields exist for database queries and list-view display ONLY.
They must NEVER be used for calculations — not on the backend, not on the frontend.

## The Rule

**Shadow fields** are scalar database fields that shadow values living
authoritatively in JSON envelopes. They exist because PostgreSQL can index a
`DecimalField` or `CharField` but cannot efficiently index a key inside a
`JSONField` for `ORDER BY`, `WHERE`, or aggregate queries.

**Allowed uses:**
- Database `filter()`, `exclude()`, `order_by()` — query performance
- List views / DataBrowser columns — display in grids and tables
- Admin `list_display` — Django admin list pages

**Forbidden uses:**
- Any calculation: `total - received`, `balance * rate`, `margin / total`
- Any business logic: `if total > threshold`, `balance == 0`
- Frontend computation: `record.total` used in arithmetic
- Serializer extraction: `data['total_amount'] = instance.total`
- Any place where the value feeds another value

**When you need the value for computation, read the JSON envelope:**
```python
# WRONG — reading denormalized scalar
margin = instance.total - instance.cost  # NO

# RIGHT — reading from JSON envelope
margin = instance.totals.get('margin')   # YES
# or if computing:
total = Decimal(str(instance.totals.get('total', 0)))
cost = Decimal(str(instance.totals.get('cost', 0)))
margin = total - cost
```

```tsx
// WRONG — reading denormalized scalar on frontend
const profit = record.total - record.cost;  // NO

// RIGHT — reading from JSON envelope
const profit = (data?.totals?.total ?? 0) - (data?.totals?.cost ?? 0);  // YES
```

## Registry

### TransactionBaseModel (all transactions: Order, Proposal, Invoice, Purchase, Workorder)

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `source_name` | `.source` JSON envelope | Query: filter by attribution source | base_transaction_model.py:222 |

**Removed fields (2026-08-24):** `total`, `balance`, `company`, `address_full`,
`email`, `phone` — these DB columns were deleted. `total` and `balance` are now
`@property` methods reading from the `totals` JSON envelope. The others are accessed
via their respective JSON aspect envelopes.

### OrgBase (Customer, Vendor, Rep, Employee, Manufacturer)

No shadow fields remain. `address_full`, `email`, `phone`, and `domain` DB columns
were deleted (2026-08-24). Values are accessed via their respective JSON aspect envelopes.

### Contact

No shadow fields remain. `address_full`, `phone`, and `domain` DB columns were
deleted (2026-08-24). Values are accessed via their respective JSON aspect envelopes.

### BillOfMaterial

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `parent_description` | `Item.description` (FK) | Display: parent item name in BOM lists | bill_of_material.py:14 |
| `child_ida` | `Item.ida` (FK) | Search: find BOM by component code | bill_of_material.py:43 |
| `child_description` | `Item.description` (FK) | Display: component name in BOM lists | bill_of_material.py:44 |

### InventoryPosition

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| Entire model | Rollup of InventoryLayer quantities | Query: aggregated position per item/site | inventory_layer.py:239 |

### UserProfile (RBAC)

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `cached_roles` | `contact.refs.roles` | Query: quick role lookups without joining | rbac.py:235 |

### Setting

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `refs.keywords` | Various config fields | Search: keyword search across settings | setting.py:98 |

## How the Totals Engine Works

The totals engine (`services/totals.py`) writes only to the `totals` JSONField
envelope — there are no scalar `total` or `balance` columns. Backward-compatible
read access is provided by `@property` methods on TransactionBaseModel that read
from the JSON envelope. Run `backfill_totals` to recompute envelopes from line
data: `python manage.py backfill_totals --all`

## Alice Enforcement

Alice's code standards scanner watches for:
- `instance.totals['total']` or direct dict access without `.get()` and a default
  (should be `instance.totals.get('total', 0)`)
- Any new `DecimalField` with `db_index=True` that shadows a JSONField key without
  being documented in this registry
- Code that assumes `total` or `balance` are database columns (they are `@property`
  methods — cannot be used in `filter()`, `order_by()`, or `update_fields`)

When a new shadow field is added, it MUST be added to this registry with its
JSON source, purpose, and model line number.
