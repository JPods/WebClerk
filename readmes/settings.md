# Settings

> Core model for storing configuration data as JSON.

---

## Model: `Setting`

**File:** `apps/core/models/setting.py`  
**Table:** `settings`  
**Inherits:** `BaseModel` (provides `id`, `is_active`, `created_at`, `updated_at`)

### Fields

| Field          | Type          | Description |
|----------------|---------------|-------------|
| `name`         | CharField     | Unique identifier within a purpose (e.g. `"transaction_defaults"`) |
| `purpose`      | CharField     | Category tag — constrained by `SETTING_PURPOSE_CHOICES` |
| `role`         | CharField     | Optional role scope (e.g. `"admin"`, `"user"`) |
| `parent_model` | CharField     | Optional canonical model key (validated against MODEL_REGISTRY) |
| `data`         | JSONField     | Arbitrary JSON payload — this is where all config lives |

### Validation

- `parent_model` is normalized to the canonical registry key on save (e.g. `"Orders"` → `"order"`).
- `full_clean()` runs automatically in `save()`, so ORM-created records are validated too.

### Virtual property

- `setting.comment` reads/writes `data["comment"]` transparently.

---

## Purpose choices

Defined in `apps/core/choices.py` → `SETTING_PURPOSE_CHOICES`:

| Purpose               | Usage |
|-----------------------|-------|
| `view_edit`           | Per-table field visibility/edit matrix by role |
| `constants`           | Global user-defined constants map |
| `db_defaults`         | Global database/platform defaults |
| `sales_defaults`      | Sales module defaults (global or per table) |
| `purchase_defaults`   | Purchasing module defaults (global or per table) |
| `accounting_defaults` | Accounting/GL/tax defaults |
| `keywords`            | Per-table keyword/denorm field config |
| `workbench_fields`    | Workbench column config |
| `detail_field_access` | Detail page field access rules |
| `qa_counters`         | QA counter configuration |
| `qa_questions`        | QA question configuration |
| `admin`               | Admin-level settings |
| `React_settings`      | Settings consumed by the React front-end |

---

## React_settings records

Settings with `purpose="React_settings"` are fetched by the React app on
startup via wcapi and cached for the session.

### transaction_defaults

**Lookup:** `name="transaction_defaults"`, `purpose="React_settings"`  
**Seeded by:** migration `core/0005_seed_transaction_defaults.py`

```json
{
  "terms": "On Order",
  "due_date_period": 1,
  "price_level": "retail",
  "priority": "standard"
}
```

| Key              | Type   | Description |
|------------------|--------|-------------|
| `terms`          | string | Default payment terms for new transactions |
| `due_date_period`| number | Days to add to transaction date for due_date |
| `price_level`    | string | Default price level (`"retail"`, `"wholesale"`, etc.) |
| `priority`       | string | Default priority (`"standard"`, `"rush"`, etc.) |

**To change defaults:** edit the `data` JSON on the Setting record directly
(admin or Django shell). No migration needed.

---

## wcapi access

```
GET /wcapi/get/?model_name=setting&name=transaction_defaults&purpose=React_settings&is_active=true&limit=1
```

All CRUD on settings goes through the standard wcapi gateway — no
per-model REST endpoints.

---

## Adding new React_settings

1. Define the `data` shape and document it in this file.
2. Create a data migration in `apps/core/migrations/` to seed the record
   (use `0005_seed_transaction_defaults.py` as a template).
3. Build or extend a React hook in `src/hooks/` to fetch and cache it.
4. No model or choice changes are needed — `React_settings` purpose
   already exists.

Alternatively, nest new sections inside an existing record's `data` JSON
to avoid extra records/fetches. A single record per purpose is preferred
when the data is always consumed together.
