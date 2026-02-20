# Denormalized Fields in `refs.links`

Every transaction (Order, Invoice, Proposal, Purchase, Work Order) and many
other records carry a `refs` JSONB column with a `links` sub-object that
holds **denormalized snapshots** of related entities.  This avoids extra API
round-trips when the frontend needs to display a customer name, email, or
phone next to a transaction.

---

## Single Source of Truth

All field lists live in **one file**:

```
common/denorm_registry.py          ← DENORM_REGISTRY dict
```

Both denormalization paths read from this registry:

| Path | File | Purpose |
|------|------|---------|
| Generic `RefsMixin.denormalize_links()` | `common/models.py` | Converts bare-ID lists → dicts on every `save()` |
| Transaction-specific `denormalize_org_links()` | `apps/transactions/services/denormalize_org_links.py` | Snapshots customer/vendor/manufacturer from FK fields |

> **Rule:** Never hard-code field lists elsewhere.  Import from
> `common.denorm_registry` instead.

---

## Org-Role Fields (customer, vendor, manufacturer, rep, employee)

Source model: **`OrgBase`** (`apps/orgs/models/base.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `display_name` | str | Company / org name (also exposed as `company` in the snapshot) |
| `email` | str | Primary email |
| `phone` | str | Primary phone |
| `address_full` | str | Denormalized full address string |
| `attention` | str | Attention line for mailing |
| `status` | str | e.g. active, prospect, retired |

### Snapshot shape

The `_snapshot_org()` function maps `display_name` → `company` so the
resulting dict looks like:

```json
{
  "id": 42,
  "company": "Acme Corp",
  "display_name": "Acme Corp",
  "email": "orders@acme.com",
  "phone": "555-1234",
  "address_full": "123 Main St, Springfield, IL 62701",
  "attention": "Jane Doe",
  "status": "active"
}
```

### TypeScript type

```ts
// src/apps/transactions/types/transactionTypes.ts
export interface OrgDenorm {
  id: number;
  ida?: string;
  display_name?: string;
  company?: string;
  email?: string;
  phone?: string;
  address_full?: string;
  attention?: string;
  status?: string;
  org_type?: string;
}
```

---

## Contact Fields

Source model: **`Contact`** (`apps/core/models/contact.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Primary key |
| `name_first` | str | First name |
| `name_last` | str | Last name |
| `display_name` | str | Computed full name |
| `company` | str | Company name |
| `title` | str | Job title |
| `role` | str | Role in context (e.g. buyer) |
| `email` | str | Primary email |
| `phone` | str | Primary phone |
| `attention` | str | Attention line |

### TypeScript type

```ts
export interface ContactDenorm {
  id: number;
  purpose?: ContactPurpose;
  role?: string;
  name_first?: string;
  name_last?: string;
  display_name?: string;
  company?: string;
  title?: string;
  email?: string;
  phone?: string;
  ida_contact?: string;
}
```

---

## Communication Records

### Email
`["id", "email", "name", "type", "is_primary"]`

### Phone
`["id", "number", "format", "name"]`

### Address
`["id", "address1", "city", "state", "zip", "country", "full"]`

### Domain
`["id", "path", "type"]`

---

## Catalog / Inventory

### Item
`["id", "name", "sku", "description", "kind", "uom"]`

### Warehouse
`["id", "name", "code"]`

---

## Financial / Accounting

| Key | Fields |
|-----|--------|
| `currency` | `id, code, name, symbol` |
| `exchangerate` | `id, from_currency, to_currency, rate` |
| `glaccount` | `id, account_credit` |
| `taxjurisdiction` | `id, name, code` |
| `paymentmethod` | `id, name, type` |
| `paymentterm` | `id, name, terms` |

---

## How Denormalization Is Triggered

| Trigger | When | Scope |
|---------|------|-------|
| `BaseModel.save()` | Every save | Converts ID-lists in `refs.links` to dicts (generic) |
| `backfill_org_links` command | Manual CLI | Snapshots customer/vendor/manufacturer from FK fields on transactions |
| WCAPI save endpoint | On create of email/phone/address/domain | Appends denormalized dict to related contact's `refs.links` |

### Running backfill after field changes

```bash
# dry-run (no changes saved)
python manage.py backfill_org_links

# commit changes
python manage.py backfill_org_links --commit

# one model only
python manage.py backfill_org_links --models order
```

---

## Adding a New Denormalized Field

1. **Add the field** to the appropriate entry in `common/denorm_registry.py`
2. **Update the TS type** in `src/apps/transactions/types/transactionTypes.ts`
3. **Run backfill** to propagate to existing records:
   ```bash
   python manage.py backfill_org_links --commit
   ```
4. **Verify** the snapshot in Django shell:
   ```python
   from common.denorm_registry import print_registry
   print_registry()
   ```

---

## Inspecting the Registry

```python
# In Django shell
from common.denorm_registry import get_denorm_fields, print_registry, describe_registry

get_denorm_fields("customer")
# ['id', 'display_name', 'email', 'phone', 'address_full', 'attention', 'status']

get_denorm_fields("contact")
# ['id', 'name_first', 'name_last', 'display_name', 'company', 'title', 'role', 'email', 'phone', 'attention']

print_registry()
# Pretty-prints all keys and their field lists
```

---

## Known Limitations

1. **No reverse propagation** — When an OrgBase record changes (e.g. phone number
   updated), existing transaction snapshots are **not** automatically refreshed.
   Run `backfill_org_links --commit` to re-snapshot.

2. **No Celery trigger** — The docstring mentions Celery-based refresh but this
   is aspirational.  Currently denormalization is only triggered on save
   (generic path) or via management command (org-specific path).
