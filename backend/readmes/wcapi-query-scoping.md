# wcapi Query Scoping — How External Users See Only Their Data

**Created:** 2026-06-29
**Principle:** All data flows through wcapi. The backend injects relationship filters so external users (customers, vendors, reps) only see data that belongs to them.

## How It Works

### The Chain

```
Browser → GET /wcapi/get/?model_name=order
       → wcapi view authenticates user
       → inject_role_filters(user, "order") builds Q object
       → Q scopes queryset: Order.objects.filter(customer_id__in=[user's customer IDs])
       → filter_response_data() strips fields not in view_fields
       → Response contains only user's orders with only allowed fields
```

### Where the Scoping Happens

**1. Authentication** — every wcapi request requires a valid JWT token. The token resolves to a Contact record.

**2. Role resolution** — `build_user_context(user)` in `apps/core/services/role_filter.py` builds:
```python
{
    "user_id": 42,
    "contact_id": 100,
    "org_ids": {
        "customer": [5, 12],     # customer orgs this contact belongs to
        "vendor": [8],            # vendor orgs
        "manufacturer": [],
        "employee": [3],
    },
    "roles": ["user_customer", "user_vendor"],
    "is_superuser": False,
}
```

**3. Query filter injection** — `inject_role_filters(user, model_name)` reads the `field_access` Setting for this model and applies `query_scope` filters:
```python
# For a customer viewing orders:
# Setting(purpose='field_access', parent_model='order').data.query_scope.customer =
#   {"customer_id__in": "$user.org_ids.customer"}
# 
# Resolves to: Order.objects.filter(customer_id__in=[5, 12])
```

**4. Field filtering** — `filter_response_data()` removes fields not in the role's `view_fields` list. A customer viewing an order sees `ida, status, total, balance, dt_created` — not `price_level, terms, cost, margin`.

**5. Edit restrictions** — on POST/save, the role's `edit_fields` list determines which fields can be written. A customer with `edit: []` can view but not modify.

### The field_access Setting Record

One Setting per model. Purpose = `field_access`. Structure:

```json
{
    "roles": {
        "admin":      { "view": "*", "edit": [...], "create": true, "delete": true },
        "manager":    { "view": "*", "edit": [...], "create": true, "delete": true },
        "sales":      { "view": [...], "edit": [...], "create": true, "delete": false },
        "warehouse":  { "view": [...], "edit": [...], "create": false, "delete": false },
        "accounting": { "view": "*", "edit": [], "create": false, "delete": false },
        "customer":   { "view": [...], "edit": [], "create": false, "delete": false },
        "vendor":     { "view": [...], "edit": [], "create": false, "delete": false },
        "rep":        { "view": [...], "edit": [], "create": false, "delete": false }
    },
    "query_scope": {
        "customer": { "customer_id__in": "$user.org_ids.customer" },
        "vendor":   { "vendor_id__in": "$user.org_ids.vendor" }
    },
    "publish": {
        "web":     ["display_name", "email", "phone"],
        "api":     ["display_name", "email", "phone", "address_full"],
        "partner": ["display_name", "email"]
    }
}
```

### Query Scope by Model

| Model | Customer sees | Vendor sees | Rep sees |
|-------|--------------|-------------|----------|
| order, invoice, proposal | customer_id = their org | vendor_id = their org | rep-linked records |
| purchase, work_order | — | vendor_id = their org | — |
| customer, vendor, etc. | id = their org only | id = their org only | all (view-only) |
| payment | contact_id = their contact | contact_id = their contact | — |
| email, phone, address | contact_id = their contact | contact_id = their contact | — |
| ledger | org_id = their org | org_id = their org | — |
| item | all active items (public catalog) | their supplied items | all |
| setting, gl_account | nothing | nothing | nothing |

### Superusers Bypass Everything

`inject_role_filters` returns an empty Q for superusers — no restrictions. This is by design. Internal staff with `is_superuser=True` see all records, all fields.

### A Contact Can Wear Multiple Hats

A contact with `customer_id=5` AND `vendor_id=8` has both roles. When viewing orders, they see orders where `customer_id=5`. When viewing purchases, they see purchases where `vendor_id=8`. The role priority system picks the most permissive role when multiple apply.

## Key Files

| File | What it does |
|------|-------------|
| `apps/core/services/role_filter.py` | `inject_role_filters()` — builds Q objects from role config |
| `apps/core/services/field_projection.py` | `filter_response_data()` — strips fields from responses |
| `apps/core/services/role_defaults.py` | Default role configs (code-level fallback) |
| `apps/core/views/wcapi.py` | GET/POST endpoints — calls inject_role_filters on every query |
| `apps/core/models/setting.py` | Setting model — stores field_access configs |
| `apps/core/choices.py` | `SETTING_PURPOSE_CHOICES` — includes 'field_access' |
| `apps/core/management/commands/seed_field_access.py` | Seeds one field_access Setting per model |

## Sync Implications

field_access Settings sync via Connection + Bundle like any other Setting. WCHQ can push policy updates to all deployments:

1. WCHQ updates `field_access:order` Setting with new role restrictions
2. Sync bundle carries the updated Setting record
3. Remote deployment receives and applies — immediately enforced on next wcapi call
4. No code deployment needed — it's data, not code

## Seeding

```bash
./bin/python manage.py seed_field_access          # create for all models
./bin/python manage.py seed_field_access --force   # overwrite existing
```

Generates 61 Settings with best-guess role configurations. Admin gets all fields (id/ida/uuid view-only). Customer/vendor/rep roles are conservative — view-only, limited fields, query-scoped to their own data.
