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
    "depends_on": {},         # Execution gating: {"action": [1,2], "workorder": [5]}
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

---

## Denormalized Fields Registry (DENORM_REGISTRY)

All field lists live in **one file**: `common/denorm_registry.py`

Both denormalization paths read from this registry:

| Path | File | Purpose |
|------|------|---------|
| Generic `RefsMixin.denormalize_links()` | `common/models.py` | Converts bare-ID lists -> dicts on every `save()` |
| Transaction-specific `denormalize_org_links()` | `apps/transactions/services/denormalize_org_links.py` | Snapshots customer/vendor/manufacturer from FK fields |

> **Rule:** Never hard-code field lists elsewhere. Import from `common.denorm_registry`.

### Org-Role Snapshot Shape (customer, vendor, manufacturer, rep, employee)

Source model: **OrgBase**. The `_snapshot_org()` function maps `display_name` -> `company`:

```json
{"id": 42, "company": "Acme Corp", "display_name": "Acme Corp",
 "email": "orders@acme.com", "phone": "555-1234",
 "address_full": "123 Main St, Springfield, IL 62701",
 "attention": "Jane Doe", "status": "active"}
```

### Contact Snapshot Fields

`id, name_first, name_last, display_name, company, title, role, email, phone, attention`

### Communication Record Fields

- **Email:** `id, email, name, type, is_primary`
- **Phone:** `id, number, format, name`
- **Address:** `id, address1, city, state, zip, country, full`
- **Domain:** `id, path, type`

### Financial/Accounting Fields

| Key | Fields |
|-----|--------|
| `currency` | `id, code, name, symbol` |
| `glaccount` | `id, account_credit` |
| `taxjurisdiction` | `id, name, code` |
| `paymentmethod` | `id, name, type` |
| `paymentterm` | `id, name, terms` |

### How Denormalization Is Triggered

| Trigger | When | Scope |
|---------|------|-------|
| `BaseModel.save()` | Every save | Converts ID-lists in `refs.links` to dicts |
| `backfill_org_links` command | Manual CLI | Snapshots customer/vendor/manufacturer on transactions |
| WCAPI save endpoint | On create of email/phone/address/domain | Appends dict to related contact's refs.links |

### Adding a New Denormalized Field

1. Add the field to `common/denorm_registry.py`
2. Update the TS type in `transactionTypes.ts`
3. Run backfill: `python manage.py backfill_org_links --commit`
4. Verify: `from common.denorm_registry import print_registry; print_registry()`

### Known Limitations

1. No reverse propagation — when OrgBase changes, existing snapshots are not auto-refreshed. Run `backfill_org_links --commit`.
2. No Celery trigger — denormalization is only triggered on save or via management command.

---

## Denormalization Playbook

### Core Rule

For any pair of related models:
1. Query/filter/constraints use FK
2. Display/search acceleration uses refs.links + refs.keywords
3. Rebuild jobs reconcile refs from FK when drift appears

### Contact <-> Communications Pattern

**Source of truth:** `Email.contact_id`, `Phone.contact_id`, etc. (FK ownership).
`Contact.email_id`, `Contact.phone_id`, etc. (primary pointers).

**Denormalize on Contact:** `contact.refs.links.email[]`, `.phone[]`, `.domain[]`, `.address[]`.
Empty buckets should be omitted entirely.

**Reverse denormalize on Communication:** `communication.refs.links.contact[]` with
key contact fields. `communication.refs.keywords[]` with lowercased search terms.

### Operational Commands

```bash
python manage.py contact_communications_maintenance [--dry-run] [--contact-id 18] [--limit 500]
python manage.py audit_refs_templates [--no-alice]
```

### Coverage by App

| App | Strategy |
|-----|---------|
| contacts | FK-first + two-way refs denormalization with communications |
| actions | FK/explicit IDs + refs for dependency graph and denormalized parties |
| communications | FK owner authoritative; refs holds contact snapshot + keywords |
| docs | FK authoritative; refs links for display context |
| orgs | FK/role FKs authoritative; refs links for related display acceleration |
| transactions | Header/line FK fields authoritative; refs links for UI display |
| all others | FK-only (no new refs denormalization until explicitly approved) |

### Guardrails

- Never treat refs.links as write authority over FK
- Do not store conflicting IDs in refs.links and FK
- Keep refs.keywords lowercase and deduplicated
- Prefer stable keys in refs.links snapshots
- Omit empty refs.links buckets

---

## Refs Inclusion Policies

### Action Denormalization

Actions denormalize links to speed navigation:
- Action -> Targets: kind auto-inferred (`transaction`, `product`, `acts_on`)
- Action -> Documents/Attachments: `kind="doc"`
- Action -> Communications: `kind="comm"`

Override inference per model via `settings.REFS_ACTION_KIND_OVERRIDES`.

Helpers: `ensure_action_all_links(action)`, `sync_action_denorm_refs(action_model, action_id)`.
Signals: `apps.support.signals.register_action_signals`.

### Assignee Links

When a line has an active Action, link the assignee to that line via
`refs.links` with `kind="assignee"`. Links are bidirectional.
`nightly_prune_refs` applies recency and caps.

---

## Refs Setting Records

### Keyword Configuration

`purpose="refs_setup"` Settings configure keyword generation and relationship denormalization:

```json
{
    "self_fields": ["email", "name_first", "name_last", "company"],
    "related_keywords": {
        "email": ["email", "attention"],
        "address": ["address1", "city", "state", "zip"],
        "customer": ["refs.keywords"]
    },
    "related_models": ["email", "address", "phone", "customer", "vendor"]
}
```

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `build_keywords_for_record()` | `apps/core/services/keywords.py` | Processes refs_setup to build keywords |
| `get_keyword_requirements()` | `apps/core/constants/keyword_requirements.py` | Loads cached refs_setup Settings |
| `refs_setting_manage` | Management command | List, view, update Settings from baseline files |

### Management

```bash
python manage.py refs_setting_manage --list
python manage.py refs_setting_manage --view --model contact --purpose refs_setup
python manage.py refs_setting_manage --update-baseline --all-models
```

Baseline files live in `readmes/baseline_setting/models/` (e.g., `contact_refs_setup.txt`).

---

## See Also

- [refs-fk-audit-report.md](refs-fk-audit-report.md) — Detailed audit of FK vs refs coexistence
- [keyword-denormalization-and-search.md](keyword-denormalization-and-search.md) — Search contract for wcapi/get with refs.keywords
- [fk-discipline.md](fk-discipline.md) — FK vs BigIntegerField policy, naming conventions, migration status
- [django-improvements.md](django-improvements.md) — Org snapshot implementation (Section 16)
