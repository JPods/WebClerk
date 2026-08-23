# PJPV Shadow Field Registry

**Established:** 2026-08-22
**Terminology updated:** 2026-08-23 — "shadow fields" is the standard term
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
| `total` | `totals.total` | Query: filter/sort by transaction total | base_transaction_model.py:149 |
| `balance` | `totals.balance` | Query: filter/sort by outstanding balance | base_transaction_model.py:151 |
| `address_full` | Contact/OrgBase addresses aspect | Display: show address in list views | base_transaction_model.py:190 |
| `email` | Contact/OrgBase emails aspect | Display: show email in list views | base_transaction_model.py:191 |
| `phone` | Contact/OrgBase phones aspect | Display: show phone in list views | base_transaction_model.py:192 |
| `company` | OrgBase.display_name | Display: show company in list views | base_transaction_model.py:188 |
| `source_name` | `.source` JSON envelope | Query: filter by attribution source | base_transaction_model.py:222 |

### OrgBase (Customer, Vendor, Rep, Employee, Manufacturer)

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `address_full` | `addresses` aspect JSON | Display/search: full address string | base.py:61 |
| `email` | `emails` aspect JSON | Display/search: primary email | base.py:62 |
| `phone` | `phones` aspect JSON | Display/search: primary phone | base.py:65 |
| `domain` | `domains` aspect JSON | Display/search: primary domain | base.py:68 |

### Contact

| Scalar Field | JSON Source | Purpose | Model Line |
|-------------|-----------|---------|------------|
| `address_full` | `addresses` aspect JSON | Display/search: full address string | contact.py:102 |
| `phone` | `phones` aspect JSON | Display/search: primary phone | contact.py:104 |
| `domain` | Email-derived | Display/search: email domain | contact.py:106 |

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

## How the Totals Engine Keeps Scalars in Sync

The totals engine (`services/totals.py`) writes both the JSON envelope AND the
denormalized scalars in a single `save()`:

```python
header.totals = totals          # JSON envelope — source of truth
header.total = _d(total)        # scalar index — for queries only
header.balance = _d(balance)    # scalar index — for queries only
header.save(update_fields=['totals', 'total', 'balance'])
```

If the scalar and the JSON disagree, the JSON wins. Run `backfill_totals` to
resync: `python manage.py backfill_totals --all`

## Alice Enforcement

Alice's code standards scanner watches for:
- `record.total` or `record.balance` used in arithmetic (not comparison for display)
- `instance.total` in Python business logic (should be `instance.totals.get(...)`)
- Any new `DecimalField` with `db_index=True` that shadows a JSONField key without
  being documented in this registry

When a new denormalized field is added, it MUST be added to this registry with its
JSON source, purpose, and model line number.
