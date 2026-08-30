# Three-Tier Select List Inheritance

**Built:** 2026-08-25 | **Where:** PJPV + Settings + record config | **Who:** Bill + Claude

## The Problem

PJPV tells React "this field is a select" but not **which select list** to use.
Different product categories need different options for the same field.
A paint supplier's `finish` list is nothing like an electronics supplier's.

## The Three Tiers

Most specific wins. Per field, not per record — a record can override one field
while inheriting everything else.

```
Tier 3: record.config.selectlists.{field}          WINS  (one specific item)
  overrides
Tier 2: record.config.selectlist_profile → Setting  |    (category: all paint items)
  overrides
Tier 1: Setting(parent_model=X).config.selectlists  |    (model: all items)
```

### Tier 1 — Model Level

Every model can have a Setting with `config.selectlists`:

```json
// Setting: parent_model="item", purpose="wc:model"
{
  "config": {
    "selectlists": {
      "status": [
        {"value": "active", "label": "Active"},
        {"value": "discontinued", "label": "Discontinued"}
      ],
      "unit_of_measure": [
        {"value": "EA", "label": "Each"},
        {"value": "CS", "label": "Case"},
        {"value": "LB", "label": "Pound"}
      ]
    }
  }
}
```

All items see these lists. Managed via `/selectlists` (SelectListBrowser).

### Tier 2 — Category Profile

A record points to a Setting that provides category-specific lists.
The profile is a **rich object** on the record — self-describing, not just an ID.

```json
// Item record (paint product)
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

The referenced Setting:

```json
// Setting id=4, ida="paint_selectlists"
{
  "config": {
    "selectlists": {
      "finish": [
        {"value": "flat", "label": "Flat / Matte"},
        {"value": "eggshell", "label": "Eggshell"},
        {"value": "satin", "label": "Satin"},
        {"value": "semi-gloss", "label": "Semi-Gloss"},
        {"value": "gloss", "label": "High Gloss"}
      ],
      "base_type": [
        {"value": "latex", "label": "Latex (Water)"},
        {"value": "oil", "label": "Oil-Based"},
        {"value": "alkyd", "label": "Alkyd"}
      ],
      "unit_of_measure": [
        {"value": "GAL", "label": "Gallon"},
        {"value": "QT", "label": "Quart"},
        {"value": "PT", "label": "Pint"}
      ]
    }
  }
}
```

Paint items get `finish` and `base_type` (new fields not on model-level).
They also get paint-specific `unit_of_measure` (GAL/QT/PT) instead of EA/CS/LB.
`status` is inherited from Tier 1 because the profile doesn't override it.

### Tier 3 — Record Level

One specific item carries its own selectlist directly:

```json
// Item record (specialty humidity-sensitive paint)
{
  "config": {
    "selectlist_profile": {
      "id": 4,
      "ida": "paint_selectlists",
      "purpose": "selectlist paint category",
      "parent_model": "item"
    },
    "selectlists": {
      "drying_humidity": [
        {"value": "low", "label": "< 40% RH"},
        {"value": "medium", "label": "40-60% RH"},
        {"value": "high", "label": "> 60% RH"}
      ]
    }
  }
}
```

This item has:
- `status` from Tier 1 (model)
- `finish`, `base_type`, `unit_of_measure` from Tier 2 (paint profile)
- `drying_humidity` from Tier 3 (its own record)

## PJPV Integration

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

## API

### Catalog mode (existing)

```
GET /wcapi/_selectlists/
```

Returns flat index of all selectlists across all Settings.

### Resolved mode (new)

```
GET /wcapi/_selectlists/?model_name=item&record_id=482
```

Returns three-tier merged selectlists for a specific record:

```json
{
  "model_name": "item",
  "record_id": 482,
  "selectlists": {
    "status": {
      "options": [{"value": "active", "label": "Active"}, ...],
      "source": "model",
      "source_detail": "Setting item_defaults (id=1)"
    },
    "finish": {
      "options": [{"value": "flat", "label": "Flat / Matte"}, ...],
      "source": "profile",
      "source_detail": "Setting paint_selectlists (id=4)"
    },
    "drying_humidity": {
      "options": [{"value": "low", "label": "< 40% RH"}, ...],
      "source": "record",
      "source_detail": "record.config.selectlists.drying_humidity"
    }
  },
  "total": 3
}
```

## Frontend Resolution

1. On model load: `useDataBrowser` fetches `Setting(parent_model=X).config.selectlists` → Tier 1
2. PJPV `selectlist_key` auto-populates from `SELECT_LIST_MAP` for any field not already covered
3. On record select: if `record.config.selectlist_profile` exists, calls `getResolvedSelectlists()` → all three tiers merged from backend
4. If only `record.config.selectlists` (no profile), merges inline without network call

## Files

| File | What |
|------|------|
| `backend/apps/core/views/system_dispatch.py` | Passes `selectlist_key` through `_pjpv_fields/` |
| `backend/common/schemas/transaction_envelopes.py` | Pydantic select fields declare `selectlist_key` |
| `backend/apps/core/views/selectlist_view.py` | `resolve_selectlists()` + resolved mode endpoint |
| `frontend/src/api/wcapi.ts` | `PjpvFieldMeta.selectlist_key` type + `getResolvedSelectlists()` |
| `frontend/src/hooks/useDataBrowser.ts` | PJPV auto-lookup + record-level useEffect |
| `frontend/src/config/selectLists.ts` | `SELECT_LIST_MAP` baseline definitions |
| `frontend/src/pages/tools/SelectListBrowser.tsx` | User-facing editor at `/selectlists` |

## Creating a Category Profile

1. Create a Setting record:
   - `ida`: descriptive slug (e.g., `paint_selectlists`)
   - `name`: human label (e.g., "Paint Category Select Lists")
   - `parent_model`: the model this applies to (e.g., `item`)
   - `purpose`: free text (e.g., `selectlist paint category`)
   - `config.selectlists`: the options arrays

2. On each record that uses this profile, set:
   ```json
   config.selectlist_profile: {
     "id": <setting_id>,
     "ida": "<setting_ida>",
     "purpose": "<what this profile is for>",
     "parent_model": "<model>"
   }
   ```

3. The profile is a rich object so the record is self-documenting.
   Looking at a record's config tells you what it inherits and why.

## Pitfalls

- **Orphan profiles**: If a Setting is deleted, records pointing to it fall back to Tier 1.
  The backend logs a warning but doesn't break.
- **Cache**: PJPV catalog is cached per session. Selectlist changes from Settings
  take effect on next page load.
- **Field names must match**: Tier 2/3 override Tier 1 by field name.
  `unit_of_measure` in the profile must exactly match `unit_of_measure` in the model Setting.
