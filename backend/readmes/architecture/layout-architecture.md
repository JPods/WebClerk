# Layout Architecture — Single Source of Truth

**Established:** 2026-08-20
**Status:** Active

## One Record Per Model

Every model's layout lives in a single `wc:model` Setting record. No separate `wc:detail_layout`, `wc:workbench_fields`, or `wc:field_access` records for layout data. One record, one place to look.

```
Setting (purpose='wc:model', parent_model='order')
  config.layout.active              → {list: "default", detail: "default", form: "default", column: "default"}
  config.layout.list.default        → list view columns
  config.layout.detail.default      → detail view fields (ordered: human → JSON → system)
  config.layout.form.default        → form sections (header, panels, json_tree, tabs)
  config.layout.column.default      → panel/column view columns
```

## Label Convention

Labels match database field names (lowercase). Users learn the schema by using the app.

- Flat fields: `company` → label `company`
- Dot-path JSON fields: `config.ship_to.company` → label `.company` (last leaf with dot prefix)
- Bracket-index fields: `action[0]` → label `action[0]`
- Section titles: lowercase (`customer`, `ship_to`, `identity`)
- Panel/tab labels: lowercase (`financials`, `comments`, `related`)

Helper function in `seed_detail_layouts.py`:
```python
def _f(field, **kwargs):
    if '.' in field:
        label = '.' + field.rsplit('.', 1)[1]
    else:
        label = field
    return {"field": field, "label": label, **kwargs}
```

## List Columns (config.layout.list.default.columns)

Array of `{field, label, width, visible, align?, format?}`. Every model has `comments.process` as a column.

| Family | Models | Column count |
|--------|--------|-------------|
| Transactions | order, proposal, invoice, purchase, workorder, requisition, receipt | 14 |
| Orgs | customer, vendor, manufacturer, employee, rep | 13 |
| Items | item | 14 |
| Contacts | contact | 11 |
| Actions | action | 10 |
| Projects | project | 11 |
| Payments | payment | 13 |
| Documents | document | 9 |
| All others | ~60 models | 5-10 (auto-generated with comments.process) |

## Detail Fields (config.layout.detail.default.fields)

Ordered array of all model fields. Ordering:
1. **Human fields** — ida, name, status, purpose, attention, etc.
2. **JSON envelope fields** — metadata, refs, prefs, config, financial, etc.
3. **System/FK fields** — id, uuid, dt_created, version, email_id, etc.

## Form Sections (config.layout.form.default)

Section-driven rendering for App view. Structure:
```json
{
  "model": "order",
  "family": "sell",
  "sections": [
    {"type": "header", "layout": "three-column", "columns": [...]},
    {"type": "line_card", "family": "sell", "toolbar": [...]},
    {"type": "panel", "content": "financials", "label": "financials"},
    {"type": "panel", "content": "notes", "label": "comments"},
    {"type": "panel", "content": "related_transactions", "label": "related"},
    {"type": "tabs", "tabs": [...]},
    {"type": "json_tree", "label": "json", "collapsed": true, "fields": [...]}
  ],
  "edit_rules": {...}
}
```

**Section types:**
- `header` — 3-column card layout with field rows
- `line_card` — transaction line items (sell or exec family)
- `panel` — collapsible panel wrapping existing TabContent (reuses financials, notes, contacts, etc.)
- `tabs` — slim tab bar for secondary content
- `json_tree` — collapsible JSON envelope viewer (collapsed by default)

19 models have form sections. Models without sections fall back to a default layout in `useDetailLayout`.

## React Components

| Component | File | Purpose |
|-----------|------|---------|
| `useDetailLayout` | `hooks/useDetailLayout.ts` | Fetches form layout from `wc:model` config.layout.form.default |
| `CollapsiblePanel` | `apps/common/components/CollapsiblePanel.tsx` | Shared collapsible wrapper with localStorage persistence |
| `PanelSectionRenderer` | `apps/transactions/components/detail/PanelSectionRenderer.tsx` | Wraps TabContent in CollapsiblePanel |
| `JsonSectionRenderer` | `apps/transactions/components/detail/JsonSectionRenderer.tsx` | Wraps JsonTree in CollapsiblePanel |
| `DataGrid` | `components/common/DataGrid.tsx` | List view — uses FieldSpec.label for headers, resolves dot-path and bracket notation |

## Seed Commands

```bash
# Seed list columns, detail fields, behaviors, field groups, access
python manage.py seed_model_definitions --force

# Seed form sections (header, panels, json_tree) into wc:model
python manage.py seed_detail_layouts

# Both together
python manage.py seed_model_definitions --force && python manage.py seed_detail_layouts
```

## Key Files

| File | What it does |
|------|-------------|
| `apps/core/management/commands/seed_model_definitions.py` | Builds wc:model config: list columns, detail fields, behaviors, access, field groups |
| `apps/core/management/commands/seed_detail_layouts.py` | Writes form sections into wc:model config.layout.form.default |
| `apps/core/services/field_behaviors.py` | Field behavior detection and field group generation |
| `hooks/useDataBrowser.ts` | Reads wc:model for list/detail layout, behaviors, field groups |
| `hooks/useDetailLayout.ts` | Reads wc:model for form sections |

## History

- 2026-08-18: Named layout format established (list, detail, form, column)
- 2026-08-19: Label convention (field names as labels, .leaf for dot-paths)
- 2026-08-19: `comment` field dropped from 5 models (contacts, documents, domains, connections, gl_accounts). `comments` JSON envelope is the single source for notes.
- 2026-08-20: Consolidated `wc:detail_layout` into `wc:model` config.layout.form.default. One Setting per model.
