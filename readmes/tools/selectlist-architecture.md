# Select List Architecture

**Created:** 2026-08-18
**Status:** Active

---

## Architecture

Every dropdown, radio group, and status picker in WC3 draws from a select list — an array of `{value, label}` pairs stored in a Setting record's `config.selectlists`. Each model's Setting owns its own select lists. There is no centralized registry — the SelectListBrowser provides the consolidated view.

### Canonical Structure

```json
{
  "config": {
    "selectlists": {
      "status": [
        { "value": "draft", "label": "Draft" },
        { "value": "open", "label": "Open" },
        { "value": "completed", "label": "Completed" }
      ],
      "price_level": [
        { "value": "retail", "label": "Retail" },
        { "value": "wholesale", "label": "Wholesale" }
      ]
    }
  }
}
```

### Rules

1. **Path:** `config.selectlists.<field_name>` — always
2. **Shape:** `[{value: string, label: string}]` — no extra fields (legacy had `sequence`, `alternate` — dropped)
3. **Ownership:** Each select list lives in the Setting that governs its model (`wc-model-order` for order fields, `company-profile` for company-wide lists)
4. **No centralization:** ida-114 (legacy admin lists) has been emptied and distributed
5. **Field name is the key:** `selectlists.status` means "the status field's options"

### Where Select Lists Live

| Setting pattern | Purpose | Example |
|----------------|---------|---------|
| `wc-model-<model>` | Model-specific field options | `wc-model-order` -> status, price_level, fob |
| `company-profile` | Company-wide lists shared across models | hold, need, job_type, priority |
| `wc:field_access` (DEV-*) | RBAC + field behaviors per model | May contain legacy options — migrate to selectlists |

### Scanner Priority

The backend scanner reads select lists in this order, skipping duplicates:

1. `config.selectlists.<field>` — **canonical** (preferred)
2. `config.behaviors.<field>.options` — legacy (wc:model)
3. `config.field_behaviors.<field>.options` — legacy (wc:field_access)
4. `config.lists.<name>.choices` — legacy (wc:admin, ida-114)
5. `config.select_lists.<name>.options` — legacy (wc:company_profile)

If a field exists in `selectlists`, the legacy paths are skipped for that field.

### How the UI Reads Select Lists

```typescript
const res = await getRecords('setting', { ida: `wc-model-${modelName}` });
const setting = res?.results?.[0];
const options = setting?.config?.selectlists?.[fieldName] || [];
```

### PJPV Integration

Pydantic schemas declare `selectlist_key` in `json_schema_extra`:

```python
type: Optional[str] = Field(
    None, title="Type",
    json_schema_extra={'widget': 'select', 'selectlist_key': 'address_type'},
)
```

The `_pjpv_fields/` endpoint serves this to React. React auto-looks up
`selectlist_key` in `SELECT_LIST_MAP` (frontend/src/config/selectLists.ts)
as a baseline — then three-tier overrides apply on top.

---

## Three-Tier Inheritance

**Built:** 2026-08-25

### The Problem

PJPV tells React "this field is a select" but not **which select list** to use.
Different product categories need different options for the same field.

### Resolution Order

Most specific wins. Per field, not per record — a record can override one field
while inheriting everything else.

```
Tier 3: record.config.selectlists.{field}          WINS  (one specific item)
  overrides
Tier 2: record.config.selectlist_profile -> Setting  |    (category: all paint items)
  overrides
Tier 1: Setting(parent_model=X).config.selectlists  |    (model: all items)
```

### Tier 1 — Model Level

Every model can have a Setting with `config.selectlists`. All items see these lists.
Managed via the Select List Browser or Setting Parade.

### Tier 2 — Category Profile

A record points to a Setting that provides category-specific lists. The profile
is a **rich object** on the record — self-describing, not just an ID.

```json
{
  "config": {
    "selectlist_profile": {
      "id": 4,
      "ida": "paint_selectlists",
      "purpose": "selectlist paint category",
      "parent_model": "item"
    }
  }
}
```

Paint items get `finish` and `base_type` (new fields not on model-level).
They also get paint-specific `unit_of_measure` (GAL/QT/PT) instead of EA/CS/LB.
`status` is inherited from Tier 1 because the profile doesn't override it.

### Tier 3 — Record Level

One specific item carries its own selectlist directly in `config.selectlists`.
This item gets `status` from Tier 1, `finish` from Tier 2, and `drying_humidity`
from Tier 3 — all at the same time.

### API

**Catalog mode (existing):**
```
GET /wcapi/_selectlists/
```
Returns flat index of all selectlists across all Settings.

**Resolved mode:**
```
GET /wcapi/_selectlists/?model_name=item&record_id=482
```
Returns three-tier merged selectlists for a specific record with `source` and
`source_detail` per field.

### Frontend Resolution

1. On model load: `useDataBrowser` fetches `Setting(parent_model=X).config.selectlists` -> Tier 1
2. PJPV `selectlist_key` auto-populates from `SELECT_LIST_MAP` for any field not already covered
3. On record select: if `record.config.selectlist_profile` exists, calls `getResolvedSelectlists()` -> all three tiers merged from backend
4. If only `record.config.selectlists` (no profile), merges inline without network call

### Creating a Category Profile

1. Create a Setting record with `ida`, `name`, `parent_model`, `purpose`, and `config.selectlists`
2. On each record, set `config.selectlist_profile` as a rich object pointing to the Setting
3. The profile is self-documenting — looking at a record's config tells you what it inherits

### Pitfalls

- **Orphan profiles**: If a Setting is deleted, records fall back to Tier 1 (warning logged, no break)
- **Cache**: PJPV catalog is cached per session. Changes take effect on next page load
- **Field names must match**: Tier 2/3 override Tier 1 by exact field name

---

## Management — User Guide

**Audience:** All users

### Three Ways to Create or Edit Select Lists

**1. Cmd+click any field label (fastest)**

On any form field in the DataBrowser, Cmd+click (Mac) or Ctrl+click (Windows) the
field label. Type options as `value:label` pairs, one per line. Click Save.

**2. Select List Browser (/selectlists)**

Alice -> Coaching Tips -> **Open Select Lists**. Browse all select lists across all
Settings. Click any list to see, add, edit, or remove options.

**3. Cmd+Shift+click for full behavior editor**

Opens the complete field behavior dialog for widget type, label, action, options, lookup model.

### Keyboard Shortcut Summary

| Shortcut | What it does |
|----------|-------------|
| **Cmd/Ctrl+click** label | Quick select list editor |
| **Shift+click** label | Field help |
| **Cmd+Shift+click** label | Full behavior editor |

### Reference Tools

| Tool | Where | What it shows |
|------|-------|---------------|
| **Setting Parade** | Alice -> Coaching -> Open Setting Parade | All Settings, select lists, field behaviors, layouts |
| **Form Parade** | Alice -> Coaching -> Open Form Parade | All print forms with sample data |
| **Select List Browser** | Alice -> Coaching -> Open Select Lists | All select lists in one place |

---

## Migration History

| Date | What |
|------|------|
| Pre-2026 | ida-114 held all select lists (116 arrays, legacy DMS) |
| 2026-08-18 | `config.selectlists` standardized across all 48 Settings |
| 2026-08-18 | ida-114 emptied — 63 lists distributed to model Settings |
| 2026-08-18 | SelectListBrowser tool page built at `/selectlists` |
| 2026-08-25 | Three-tier inheritance built |
| 2026-08-26 | User guide + keyboard shortcuts documented |

## Alice Integration

Alice should:
- Watch for new select lists added to model Settings
- Flag when the same field name has different options across models
- Recommend harmonization when overlapping lists diverge
- Track option usage: which values are actually used vs. defined but never chosen

## Files

| File | What |
|------|------|
| `apps/core/views/selectlist_view.py` | Backend scanner, API endpoint, `resolve_selectlists()` |
| `apps/core/urls.py` | Route registration |
| `React2025/src/pages/tools/SelectListBrowser.tsx` | Frontend tool page |
| `React2025/src/routes/Routes.ts` | Route `/selectlists` |
| `React2025/src/routes/protectedRoutesConfig.tsx` | Route registration |
| `backend/apps/core/views/system_dispatch.py` | Passes `selectlist_key` through `_pjpv_fields/` |
| `backend/common/schemas/transaction_envelopes.py` | Pydantic select fields declare `selectlist_key` |
| `frontend/src/api/wcapi.ts` | `PjpvFieldMeta.selectlist_key` type + `getResolvedSelectlists()` |
| `frontend/src/hooks/useDataBrowser.ts` | PJPV auto-lookup + record-level useEffect |
| `frontend/src/config/selectLists.ts` | `SELECT_LIST_MAP` baseline definitions |
