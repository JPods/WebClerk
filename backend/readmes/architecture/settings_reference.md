# Settings Model Reference

The **Setting** model provides a flexible key-value store for configuration data throughout the system. Each record is identified by a combination of `purpose`, `model_target`, and optional `name` or `role` fields.

> **Frontend Reference:** See [React2025 Settings API](../../../../React2025/readmes/topics/settings-api.md) for TypeScript interfaces and API call examples.
>
> ⚠️ **Keep in Sync:** When modifying schemas or adding purposes here, update the R25 settings-api.md accordingly.

---

## Model Schema

| Field         | Type         | Description                                         |
|---------------|--------------|-----------------------------------------------------|
| `id`          | int          | Primary key (auto-increment)                        |
| `name`        | varchar(255) | Human-readable identifier (optional)                |
| `purpose`     | varchar(255) | Categorizes the setting type (see below)            |
| `role`        | varchar(255) | Role-specific settings (e.g., "user", "admin")      |
| `model_target`| varchar(255) | Canonical model name this setting applies to        |
| `data`        | JSON         | The actual configuration payload                    |

---

## Purpose Categories

Settings are categorized by `purpose`. The current registered purposes are:

| Purpose               | Description                                    | Singleton | Per-Model |
|-----------------------|------------------------------------------------|:---------:|:---------:|
| `view_edit`           | Field visibility/edit matrix by role           |           | ✓         |
| `constants`           | User-defined global constants                  | ✓         |           |
| `db_defaults`         | Database/platform defaults                     | ✓         |           |
| `sales_defaults`      | Sales module defaults                          | ✓         | ○         |
| `purchase_defaults`   | Purchasing module defaults                     | ✓         | ○         |
| `accounting_defaults` | Accounting/GL/tax defaults                     | ✓         |           |
| `keywords`            | Fields to denormalize into search keywords     |           | ✓         |
| `workbench_fields`    | Columns to display in list workbenches         |           | ✓         |
| `detail_field_access` | Field visibility/editability in detail views   |           | ✓         |
| `qa_counters`         | Auto-increment counters for Q&A IDs            | ✓         |           |
| `qa_questions`        | Question definitions with templates            |           | ✓ (group) |
| `admin`               | Administrative singletons (keyed by `name`)    | ✓ (named) |           |

**Legend:** ✓ = required, ○ = optional per-model override

---

## Setting Patterns

### 1. Singleton Settings

A single record for global configuration. Query by `purpose` alone:

```python
# Python
setting = Setting.objects.get(purpose='db_defaults')
config = setting.data
```

```typescript
// TypeScript (React)
const setting = await fetchSetting({ purpose: 'db_defaults' });
```

### 2. Per-Model Settings

One record per model. Query by `purpose` + `model_target`:

```python
# Python
setting = Setting.objects.filter(
    purpose='workbench_fields',
    model_target='order'
).first()
```

```typescript
// TypeScript
const setting = await fetchSetting({
  purpose: 'workbench_fields',
  model_target: 'order'
});
```

### 3. Role-Based Settings

Per-model settings that vary by role:

```python
# Python
setting = Setting.objects.filter(
    purpose='view_edit',
    model_target='order',
    role='user'
).first()
```

### 4. Group-Based Settings

Settings keyed by a logical group name (not a model):

```python
# Python - QA questions for "Planning" group
setting = Setting.objects.filter(
    purpose='qa_questions',
    name='Planning'
).first()
```

---

## Detailed Purpose Specifications

### `workbench_fields`

Controls which columns appear in list/workbench views.

**Lookup:** `purpose='workbench_fields'` + `model_target`

```json
{
  "model_target": "order",
  "purpose": "workbench_fields",
  "data": {
    "list": ["id", "customer_name", "order_date", "total", "status"],
    "detail": ["id", "customer_name", "order_date", "ship_date", "total", "status", "notes"]
  }
}
```

---

### `detail_field_access`

Controls field visibility and editability in detail/edit views.

**Lookup:** `purpose='detail_field_access'` + `model_target`

```json
{
  "model_target": "order",
  "purpose": "detail_field_access",
  "data": {
    "hidden": ["internal_notes", "legacy_id"],
    "readOnly": ["created_at", "created_by", "order_number"]
  }
}
```

---

### `view_edit`

Matrix defining field access by role. Supports row-level permissions.

**Lookup:** `purpose='view_edit'` + `model_target` + `role`

```json
{
  "model_target": "order",
  "purpose": "view_edit",
  "role": "user",
  "data": {
    "fields": {
      "discount_pct": { "view": true, "edit": false },
      "cost": { "view": false, "edit": false },
      "notes": { "view": true, "edit": true }
    }
  }
}
```

---

### `keywords`

Specifies which fields to denormalize into the searchable keywords array.

**Lookup:** `purpose='keywords'` + `model_target`

```json
{
  "model_target": "contact",
  "purpose": "keywords",
  "data": {
    "fields": ["name", "email", "phone", "company_name"],
    "refs": {
      "company": ["name", "account_number"]
    }
  }
}
```

---

### `constants`

Global user-defined constants for formulas, calculations, etc.

**Lookup:** `purpose='constants'` (singleton)

```json
{
  "purpose": "constants",
  "data": {
    "tax_rate_default": 0.0825,
    "shipping_markup": 1.15,
    "payment_terms_days": 30
  }
}
```

---

### `db_defaults`

Platform-wide database defaults.

**Lookup:** `purpose='db_defaults'` (singleton)

```json
{
  "purpose": "db_defaults",
  "data": {
    "currency": "USD",
    "date_format": "YYYY-MM-DD",
    "timezone": "America/Chicago"
  }
}
```

---

### `sales_defaults`

Sales module defaults. Can be global or per-model override.

**Lookup:** `purpose='sales_defaults'` (global) or + `model_target` (override)

```json
{
  "purpose": "sales_defaults",
  "data": {
    "default_terms": "Net 30",
    "auto_confirm": false,
    "require_po": true
  }
}
```

---

### `qa_counters`

Singleton tracking auto-increment counters for QuestionAnswer records.

**Lookup:** `purpose='qa_counters'` (singleton)

```json
{
  "purpose": "qa_counters",
  "data": {
    "question_max": 45,
    "answer_max": 124
  }
}
```

See: [qa_implementation_plan.md](qa/qa_implementation_plan.md) for full specification.

---

### `qa_questions`

Question definitions for a logical group (e.g., "Planning", "Prepress").

**Lookup:** `purpose='qa_questions'` + `name` (group name)

```json
{
  "purpose": "qa_questions",
  "name": "Planning",
  "data": {
    "template": {
      "allow_freeform": false,
      "allow_multiple": false,
      "require_image": false,
      "image_max": 3,
      "image_types": ["jpg", "png", "pdf"]
    },
    "questions": [
      {
        "question_id": 1,
        "prompt": "Job Type?",
        "choices": ["Digital", "Offset", "Large Format"],
        "require_image": true
      },
      {
        "question_id": 2,
        "prompt": "Special Instructions?",
        "allow_freeform": true
      }
    ]
  }
}
```

**Resolution Order:** `question.option ?? template.option ?? system_default`

See: [qa_implementation_plan.md](qa/qa_implementation_plan.md) for full specification.

---

### `admin`

Administrative singleton settings keyed by `name`. Each provides a shared
configuration dataset that the frontend can fetch for runtime use.

**Lookup:** `purpose='admin'` + `name`

#### `popup_choices` (id 114)

Normalized legacy wc2 popup/choice lists for select dropdowns in r25.

**Seeded by:** `python manage.py create_popup_choices`

```json
{
  "purpose": "admin",
  "name": "popup_choices",
  "data": {
    "meta": {
      "source": "wc2 popups/popupchoices migration",
      "created_at": "2026-02-23T...",
      "total_lists": 116,
      "total_choices": 209
    },
    "lists": {
      "status": {
        "list_name": "Status",
        "wc2_array_name": "<>aStatus",
        "where_used": "...",
        "choices": [
          { "value": "INVOICE", "label": "INVOICE", "alternate": "", "sequence": 0 },
          { "value": "APPROVED", "label": "APPROVED", "alternate": "", "sequence": 0 }
        ]
      },
      "salutation": {
        "list_name": "Salutation",
        "wc2_array_name": "<>aSalutation",
        "where_used": "",
        "choices": [
          { "value": "Ms", "label": "Ms", "alternate": "", "sequence": 0 },
          { "value": "Mrs.", "label": "Mrs.", "alternate": "", "sequence": 0 },
          { "value": "Mr.", "label": "Mr.", "alternate": "", "sequence": 0 },
          { "value": "Dr.", "label": "Dr.", "alternate": "", "sequence": 0 }
        ]
      }
    }
  }
}
```

**Key lists** (116 total): `status` (29 choices), `actions` (12), `type_sale` (6),
`salutation` (4), `prospect` (5), `reasons` (4), `activities` (4),
`job_type` (7), `items_type` (6), `orders_profile1` (7), etc.

#### `layout_status` (id 113)

Tracks which r25 model layout files exist (Detail, List, Dialog, Panel)
and their implementation status.

**Seeded by:** `python manage.py create_layout_status`

See: [layout-maintenance.md](../../../../React2025/readmes/layout-maintenance.md) for full specification.

```json
{
  "purpose": "admin",
  "name": "layout_status",
  "data": {
    "layouts": [
      {
        "app": "transactions",
        "model": "order",
        "detail_exists": true,
        "list_exists": true,
        "dialog_exists": false,
        "panel_exists": false,
        "detail_status": "",
        "list_status": "",
        "dialog_status": "",
        "panel_status": "",
        "assigned_to": ""
      }
    ]
  }
}
```

---

## API Usage

### Fetching Settings (GET)

```typescript
// Via wcapi
const res = await apiClient.get('/wcapi/get/', {
  params: {
    model_name: 'setting',
    purpose: 'workbench_fields',
    model_name_filter: 'order'  // maps to model_target
  }
});
const setting = res.data.data.results[0];
```

### Creating/Updating (POST)

```typescript
await apiClient.post('/wcapi/save/', {
  model_name: 'setting',
  id: existingId,  // omit for create
  purpose: 'workbench_fields',
  model_target: 'order',
  data: { list: [...], detail: [...] }
});
```

---

## Validation Rules

1. **model_target** is validated against the model registry (canonical names only)
2. **purpose** should match one of `SETTING_PURPOSE_CHOICES` (soft validation)
3. **data** must be valid JSON; schema depends on purpose
4. Singleton settings should have exactly one record per purpose
5. Per-model settings should have exactly one record per (purpose, model_target) pair

---

## Adding New Purposes

1. Add choice to `apps/core/choices.py` → `SETTING_PURPOSE_CHOICES`
2. Document schema in this file
3. Create helper functions for fetching/saving (if frequently used)
4. Add migration to seed initial data if needed

```python
# apps/core/choices.py
SETTING_PURPOSE_CHOICES: Final[ChoiceList] = (
    ...
    ("new_purpose", "New Purpose Description"),
)
```

---

## Related Files

| File | Description |
|------|-------------|
| [apps/core/models/setting.py](../../../apps/core/models/setting.py) | Django model definition |
| [apps/core/choices.py](../../../apps/core/choices.py) | Purpose choices |
| [React2025/src/api/wcapi.ts](../../../../React2025/src/api/wcapi.ts) | API helper functions |
| [qa_implementation_plan.md](qa/qa_implementation_plan.md) | Q&A specific settings |
| [create_popup_choices.py](../../../apps/core/management/commands/create_popup_choices.py) | Seed popup_choices admin setting |
| [create_layout_status.py](../../../apps/core/management/commands/create_layout_status.py) | Seed layout_status admin setting |
| [React2025 layout-maintenance.md](../../../../React2025/readmes/layout-maintenance.md) | Layout status detailed docs |
