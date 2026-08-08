# DataBrowser Layout Schema

**Location:** `common/schemas/setting.py`
**Stored on:** Setting records with `purpose='workbench_fields'`
**Path:** `config.db.list[]`, `config.db.detail[]`, `config.db.panel[]`, `config.db.card[]`

---

## The Problem This Solves

Every model in WebClerk needs four views of its data. Without a typed schema,
each developer invents their own field list format — some use bare strings,
some use objects with different key names, some forget widths, some add keys
that nothing reads. The result is layouts that break silently when the UI
changes.

The schema enforces one structure. Alice validates against it. Users get
predictable behavior.

---

## Four Layout Types

| Layout | Context | Example |
|--------|---------|---------|
| `db.list` | Scanning many records | DataBrowser grid — columns, widths, sort order |
| `db.detail` | Working one record fully | Contact detail — all fields, sections, groups |
| `db.panel` | Related records inside a detail view | Order lines on an order, actions on a project |
| `db.card` | Abbreviated popup / tile | Action card in Kanban, quick-view hover |

Each is an array of `DbFieldSpec` objects. Same schema, different field
selection and widths per context.

---

## DbFieldSpec

Every item in `db.list[]`, `db.detail[]`, `db.panel[]`, and `db.card[]` is a
`DbFieldSpec`:

```json
{
  "field": "company",
  "width": 180,
  "align": "left",
  "visible": true,
  "format": null,
  "wrap": false,
  "frozen": false,
  "summary": null,
  "alice_note": null,
  "type_hint": null
}
```

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `field` | string | The model field name. Must match a real field on the model. |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | int or null | null | Column width in pixels. User sets via drag or type. null = use smart default (120px fallback). |
| `min_width` | int or null | null | Minimum width in pixels. |
| `max_width` | int or null | null | Maximum width in pixels. |
| `align` | "left" / "center" / "right" / null | null | Text alignment. null = auto-detect from field type. |
| `visible` | bool | true | Whether the field is shown. false = hidden but preserved in layout order. |
| `format` | string or null | null | Display format override. One of: `currency`, `percent`, `date`, `number`, `json`, `phone`, `masked`. |
| `wrap` | bool | false | true = word-wrap text. false = truncate with ellipsis. |
| `frozen` | bool | false | true = sticky left column (always visible during horizontal scroll). |
| `summary` | "sum" / "avg" / "count" / null | null | Footer summary function for this column. |
| `alice_note` | string or null | null | Alice's annotation — why this field is included or how to use it. |
| `type_hint` | string or null | null | Override the auto-detected widget type from field_behaviors. |

### What is NOT in DbFieldSpec

- **No `label`** — labels come from field_behaviors or the field name itself.
- **No `sortable`** — all fields are sortable in db.list.
- **No `editable`** — edit permissions come from field_access Settings, not layout.
- **No `color`** — row coloring rules are separate (RowColorRule in DataGrid).

---

## DbNamedView

A named snapshot of all four layout types. Users save these to switch between
different views of the same model.

```json
{
  "name": "compact",
  "list": [DbFieldSpec, ...],
  "detail": [DbFieldSpec, ...],
  "panel": [DbFieldSpec, ...],
  "card": [DbFieldSpec, ...]
}
```

Protected view names that cannot be overwritten: `initial`, `alice_guess`.

---

## DbLayout

The top-level container. Lives at `config.db` on the Setting record.

```json
{
  "db": {
    "list": [DbFieldSpec, ...],
    "detail": [DbFieldSpec, ...],
    "panel": [DbFieldSpec, ...],
    "card": [DbFieldSpec, ...],
    "views": [DbNamedView, ...]
  }
}
```

---

## Where It Lives

```
Setting (one per model)
  purpose: "workbench_fields"
  parent_model: "contact"  (or "order", "item", etc.)
  config:
    db:
      list: [{field: "ida", width: 100, ...}, ...]
      detail: [{field: "name_first", width: 120, ...}, ...]
      panel: []
      card: []
      views: [{name: "compact", list: [...], ...}]
```

One Setting record per model. One source of truth. No per-user duplication
(that may come later via per-contact layout overrides, but the Setting is
always the baseline).

---

## Smart Defaults

When a field has no explicit width, align, or format in the spec, the frontend
applies smart defaults based on field name patterns:

| Pattern | Width | Align | Format |
|---------|-------|-------|--------|
| `company`, `display_name` | 180 | left | — |
| `ida`, `sku` | 100 | left | — |
| `phone*` | 120 | left | phone |
| `email*` | 180 | left | — |
| `price*`, `total`, `balance` | 100 | right | currency |
| `dt_*`, `*_date` | 100 | center | date |
| `is_*` | 50 | center | — |
| `qty*`, `quantity` | 60 | right | — |
| `notes`, `comments` | 200 | left | — (wrap) |

See `getDefaultFieldSpec()` in `useDataBrowser.ts` for the complete list.
User-set values in DbFieldSpec always win over smart defaults.

---

## Validation

**Backend:** `DbFieldSpec`, `DbNamedView`, and `DbLayout` are Pydantic models
with `extra = 'forbid'`. Unknown keys are rejected. This prevents drift.

**Frontend:** `toFieldSpecs()` in `useDataBrowser.ts` normalizes bare strings
to `DbFieldSpec` objects and applies smart defaults.

**Alice:** Should validate layouts against this schema when:
- A user saves a layout
- A layout is imported via sync
- A layout is generated by Alice's layout guesser

---

## Migration

Existing data was migrated from the old flat structure (`config.list`,
`config.detail`, `config.views`) to the new nested structure (`config.db.*`)
by `manage.py migrate_db_layouts`. The migration:

1. Converts bare string field names to `{field: "name", visible: true}`
2. Preserves existing FieldSpec dicts (width, align, etc.)
3. Moves from `config.list` to `config.db.list`
4. Adds empty `panel` and `card` arrays
5. Removes old top-level keys
6. Is idempotent — skips records already migrated

---

## For Alice

Alice should know:
1. Every model gets one `workbench_fields` Setting with `config.db`
2. `db.list` controls what users see in the DataBrowser grid
3. `db.detail` controls what users see when they click a record
4. `db.panel` controls embedded related-record lists (e.g., order lines)
5. `db.card` controls popup/tile views (e.g., Kanban cards)
6. Unknown keys in DbFieldSpec are rejected — don't invent new ones
7. `field` must match a real model field — validate against the model's field list
8. `width` is in pixels, set by the user — don't override without asking
9. Smart defaults handle most cases — only set explicit values when the default is wrong
