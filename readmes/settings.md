# Settings records: purposes and shapes


<!-- TOC START -->

## Table of Contents

- [Settings records: purposes and shapes](#settings-records-purposes-and-shapes)
  - [Table of Contents](#table-of-contents)
  - [Recognized purposes](#recognized-purposes)

<!-- TOC END -->

This document catalogs the canonical purposes for rows in the `settings` table and the expected JSON shapes for each.

Applies to model: `apps.core.models.Setting` (db_table=`settings`). Fields of note:

- `purpose`: categorizes the setting entry
- `table_name` (optional): scope to a specific model/table (e.g., `transactions_proposalline`)
- `role` (optional): role-specific variant (e.g., `USER`, `ADMIN`, `PUBLIC`)
- `data` (JSON): payload; shape depends on `purpose`

Recommended uniqueness: at most one active row per `(purpose, table_name, role)` combination. If multiple exist, the system should pick the most recent by `dt_modified`.

## Recognized purposes

1. view_edit (field-level authorization)

Scope: requires `table_name`. Defines per-role field lists.

Shape (data):

```json
{
  "USER":   {"view": ["id", "status"], "edit": ["status"]},
  "ADMIN":  {"view": ["id", "status", "probability"], "edit": ["status", "probability"]},
  "PUBLIC": {"view": ["id"], "edit": []}
}
```

Notes:

- Responses filter to `view` set; writes limited to `edit` set.
- See: readmes/readme.md → Field-Level Authorization (view_edit)

1. constants (user defined CONSTANTS)

Scope: global or per-role. `table_name` typically null.

Shape (data): simple flat map of constant names to values.

```json
{
  "COMPANY_NAME": "Acme Inc.",
  "PRIMARY_CURRENCY": "USD",
  "DEFAULT_LOCALE": "en-US"
}
```

1. db_defaults (Database defaults)

Scope: global. Operational defaults for the platform.

Shape (data):

```json
{
  "pagination": {"page_size": 50, "max_page_size": 500},
  "throttle": {"user_per_day": 10000, "anon_per_day": 100},
  "features": {"open_read": false, "jwt_only": false}
}
```

1. sales_defaults

Scope: global or by `table_name` for a specific sales model.

Shape (data):

```json
{
  "currency": "USD",
  "terms": "Net 30",
  "warehouse_id": 1,
  "price_list": "STANDARD",
  "tax_code": "TAXABLE"
}
```

1. purchase_defaults

Scope: global or by `table_name` for a specific purchasing model.

Shape (data):

```json
{
  "currency": "USD",
  "terms": "Net 30",
  "receive_requires_po": true,
  "default_vendor_id": null
}
```

1. accounting_defaults

Scope: global. GL and tax mappings.

Shape (data):

```json
{
  "gl_accounts": {
    "revenue": "4000",
    "cogs": "5000",
    "inventory": "1200",
    "ap": "2000",
    "ar": "1100"
  },
  "tax": {
    "default_rate": 0.07,
    "rounding": "half_up"
  }
}
```

---

Conventions:

- `purpose` values are lowercase snake case: `view_edit`, `constants`, `db_defaults`, `sales_defaults`, `purchase_defaults`, `accounting_defaults`.
- Prefer small, composable settings over monoliths; split by `table_name` or `role` as needed.
- Changes should invalidate caches via `dt_modified` checks; consumers should refresh on change.
