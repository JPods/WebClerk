# Refs Pattern: Links & Keywords

**Purpose:** Universal denormalization layer for relationships and search across all BaseModel descendants.

---

## Core Architecture

Every model inheriting `BaseModel` (via `RefsMixin`) has a `refs` JSONField:

```python
refs = {
    "keywords": [],           # Searchable terms (names, idas, codes)
    "tags": [],               # User-created tags
    "categories": [],         # Classification tags
    "links": {                # Denormalized relationship snapshots
        "<role>": [{id, ...display_fields}],
    },
    "parents": [],            # Gantt parent IDs (actions)
    "depends_on": {},         # Execution gating: {"action": [1,2], "work_order": [5]}
    "related_ids": [],        # Generic related record IDs
}
```

---

## Design Principles

### 1. FK = Source of Truth, refs.links = Cache

```
customer_id (FK)  ──────►  refs.links.customer[{id, company, email, ...}]
       │                              │
       │                              │
   Authority                    Denormalized
   for queries                  for display
```

- **Query by FK:** `Order.objects.filter(customer_id=123)`
- **Display from refs:** `order.refs.links.customer[0].company` — no join needed

### 2. Multiple Relationships per Role

```python
refs.links.customer = [
    {"id": 42, "company": "Primary Customer", ...},   # FK customer
    {"id": 99, "company": "Ship-To Customer", ...},   # Additional via refs
]
```

- First entry typically matches FK
- Additional entries represent secondary relationships (ship-to, bill-to, etc.)

### 3. Keywords for Search

```python
refs.keywords = ["acme corp", "ACM-001", "jane doe", "manufacturing"]
```

- Lowercased for case-insensitive search
- Populated by Celery from related records (customer name, item sku, contact name)
- Queried via PostgreSQL GIN index: `refs__keywords__contains=["acme"]`

---

## Standard Link Roles by Model

### Transactions (Order, Invoice, Proposal, Purchase)

| Role | Source | Fields Captured |
|------|--------|-----------------|
| `customer` | FK `customer_id` | id, company, ida, address_full, email, phone, attention |
| `vendor` | FK `vendor_id` | id, company, ida, address_full, email, phone, attention |
| `manufacturer` | FK `manufacturer_id` | id, company, ida |
| `contact` | FK `contact_id` | id, name, email, phone |
| `employee` | refs only | id, name, role (salesperson, production, etc.) |
| `rep` | refs only | id, name, role, commission% |

### Items

| Role | Source | Fields Captured |
|------|--------|-----------------|
| `manufacturer` | FK | id, company |
| `vendor` | FK/refs | id, company (preferred vendors) |
| `category` | refs | id, name |

### Contacts

| Role | Source | Fields Captured |
|------|--------|-----------------|
| `org` | FK `org_id` | id, company |
| `email` | refs | id, email, type |
| `phone` | refs | id, number, type |
| `address` | refs | id, type, address fields |

### Projects

| Role | Source | Fields Captured |
|------|--------|-----------------|
| `customer` | FK | id, company |
| `manager` | refs | id, name |
| `contact` | refs | id, name, email |

---

## Implementation Files

| File | Purpose |
|------|---------|
| `common/models.py` RefsMixin | `add_keyword()`, `add_tag()`, `denormalize_links()` |
| `common/refs/links.py` | `upsert_link()`, `remove_link()`, `ensure_bidirectional()` |
| `common/refs/contact_refs.py` | Contact-specific normalization for save/response |
| `common/refs/policy.py` | Time/count pruning rules for refs.links |
| `common/refs/tasks.py` | Celery maintenance: `prune_refs_for_owner()`, `nightly_prune_refs()` |
| `apps/transactions/services/denormalize_org_links.py` | Org snapshot builder for transactions |

---

## Maintenance Commands

| Command | Purpose |
|---------|---------|
| `update_keywords` | Batch rebuild `refs.keywords` |
| `denormalize_links` | Batch rebuild `refs.links` snapshots |
| `backfill_org_links` | Populate customer/vendor/manufacturer on transactions |
| `populate_project_contacts` | Build `project.refs.links.contact[]` |

---

## Frontend Consumption (React)

```typescript
// TypeScript interface
interface EntityRefs {
  keywords?: string[];
  tags?: string[];
  links?: {
    customer?: OrgDenorm[];
    vendor?: OrgDenorm[];
    manufacturer?: OrgDenorm[];
    contact?: ContactDenorm[];
    employee?: EmployeeDenorm[];
    rep?: RepDenorm[];
    document?: number[];
    [key: string]: unknown;
  };
}

// Usage - display without API call
const customerName = record.refs?.links?.customer?.[0]?.company ?? "Unknown";
```

---

## When to Use Each Pattern

| Need | Use |
|------|-----|
| Query/filter records | FK column (`customer_id=123`) |
| Display related info | `refs.links.customer[0].company` |
| Multiple orgs per role | `refs.links.customer[1+]` |
| Full-text search | `refs.keywords` contains company names, idas |
| M2M without junction table | `refs.links.<role>[]` |
| Audit/lineage tracking | `refs.links.linkage`, `flow.source/children` |

---

## Benefits

1. **No record locking** — display data is denormalized, no joins needed
2. **Flexible schema** — new relationship types = new keys, no migrations
3. **Unified API** — frontend always reads `record.refs.links.<role>`
4. **Searchable** — keywords indexed via PostgreSQL GIN
5. **Celery-maintained** — async updates, no blocking on save

---

## See Also

- [refs-fk-audit-report.md](refs-fk-audit-report.md) — Detailed audit of FK vs refs coexistence
- [refs-denormalization-playbook.md](refs-denormalization-playbook.md) — FK-first denormalization process with Contact/Communication examples
- [django-improvements.md](django-improvements.md) — Org snapshot implementation (Section 16)
- [maintenance.md](../../maintenance.md) — Management command and maintenance runbook
