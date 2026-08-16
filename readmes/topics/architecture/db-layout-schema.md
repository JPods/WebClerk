# DataBrowser Layout Schema

**Location:** `common/schemas/setting.py`
**Stored on:** Setting records with `purpose='workbench_fields'`
**Path:** `config.layout.*`

---

## The Core Idea

Every named layout carries its own field data AND declares which layouts it pairs
with in the other two types. No separate "views" layer. The layout IS the view.

Three rendering paths exist in WC3:

| Path | Key | Renderer | What it is |
|------|-----|----------|------------|
| **List** | `layout.list` | DataBrowser grid | Columns, widths, sort — scanning many records |
| **Detail** | `layout.detail` | DataBrowser field grid | db.json admin entry — all fields, groups |
| **UI** | `layout.ui` | DynamicDetail / ui.json | Business forms — user-facing app mode |

The App/Admin toggle in the top bar switches between **detail** (Admin) and **ui** (App)
for the right panel. The list always controls the left panel.

---

## Layout Structure

```json
{
  "layout": {
    "active": {
      "list": "bill_layout",
      "detail": "default",
      "ui": "default"
    },
    "list": {
      "default": {
        "detail": "default",
        "ui": "default",
        "columns": [
          { "field": "ida", "width": 100, "align": "left" },
          { "field": "name", "width": 180 },
          { "field": "status", "width": 80, "align": "center" }
        ]
      },
      "bill_layout": {
        "detail": "compact",
        "ui": "default",
        "columns": [
          { "field": "name", "width": 200 },
          { "field": "parent_model", "width": 120 },
          { "field": "purpose", "width": 100 }
        ]
      }
    },
    "detail": {
      "default": {
        "list": "default",
        "ui": "default",
        "fields": [
          { "field": "name", "width": 200 },
          { "field": "scope", "width": 100 },
          { "field": "config" }
        ]
      },
      "compact": {
        "list": "bill_layout",
        "ui": "default",
        "fields": [
          { "field": "name", "width": 200 },
          { "field": "status" }
        ]
      }
    },
    "ui": {
      "default": {
        "list": "default",
        "detail": "default",
        "fields": [
          { "field": "name", "width": 200 },
          { "field": "config" }
        ]
      }
    }
  }
}
```

### How It Works

1. **`active`** tracks which named layout is currently selected for each type.
   On load, read `active` and render accordingly.

2. **Pick any layout — the other two follow.** Switch list to "bill_layout" and
   detail flips to "compact", ui stays "default" (because that's what bill_layout declares).

3. **Pairings are independent, not bidirectionally enforced.** List "bill_layout"
   says `detail: "compact"`. Detail "compact" says `list: "default"`. That's fine —
   each entry point is its own opinion. If you force bidirectional consistency
   you're back to a views layer. The asymmetry is a feature.

4. **"default" always exists, always the fallback.** If a layout points to a name
   that doesn't exist, fall back to "default" silently. "default" can be edited
   but never deleted.

---

## DbFieldSpec

Every item in a layout's `columns` or `fields` array is a `DbFieldSpec`:

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
| `width` | int or null | null | Column width in pixels. null = smart default (120px fallback). |
| `min_width` | int or null | null | Minimum width in pixels. |
| `max_width` | int or null | null | Maximum width in pixels. |
| `align` | "left" / "center" / "right" / null | null | Text alignment. null = auto-detect from field type. |
| `visible` | bool | true | Whether the field is shown. false = hidden but preserved in order. |
| `format` | string or null | null | Display format: `currency`, `percent`, `date`, `number`, `json`, `phone`, `masked`. |
| `wrap` | bool | false | true = word-wrap. false = truncate with ellipsis. |
| `frozen` | bool | false | true = sticky left column (always visible during horizontal scroll). |
| `summary` | "sum" / "avg" / "count" / null | null | Footer summary function. |
| `alice_note` | string or null | null | Alice's annotation — why this field is included. |
| `type_hint` | string or null | null | Override auto-detected widget type from field_behaviors. |

### What is NOT in DbFieldSpec

- **No `label`** — labels come from field_behaviors or the field name.
- **No `sortable`** — all fields are sortable.
- **No `editable`** — edit permissions come from field_access Settings.
- **No `color`** — row coloring rules are separate (RowColorRule).

---

## Additional Layout Types

Two more layout types exist but are not part of the pairing system:

| Layout | Context | Example |
|--------|---------|---------|
| `panel` | Related records inside a detail view | Order lines on an order, actions on a project |
| `card` | Abbreviated popup / tile | Action card in Kanban, quick-view hover |

These are stored alongside the main layout but are not paired — they are always
rendered in their specific context regardless of which list/detail/ui layout is active.

---

## Where It Lives

```
Setting (one per model)
  purpose: "workbench_fields"
  parent_model: "contact"  (or "order", "item", etc.)
  config:
    layout:
      active: { list: "default", detail: "default", ui: "default" }
      list:
        default: { detail: "default", ui: "default", columns: [...] }
      detail:
        default: { list: "default", ui: "default", fields: [...] }
      ui:
        default: { list: "default", detail: "default", fields: [...] }
      panel: [...]
      card: [...]
```

One Setting record per model. One source of truth.

---

## Smart Defaults

When a field has no explicit width, align, or format, the frontend applies
smart defaults based on field name patterns:

| Pattern | Width | Align | Format |
|---------|-------|-------|--------|
| `company`, `display_name` | 180 | left | -- |
| `ida`, `sku` | 100 | left | -- |
| `phone*` | 120 | left | phone |
| `email*` | 180 | left | -- |
| `price*`, `total`, `balance` | 100 | right | currency |
| `dt_*`, `*_date` | 100 | center | date |
| `is_*` | 50 | center | -- |
| `qty*`, `quantity` | 60 | right | -- |
| `notes`, `comments` | 200 | left | -- (wrap) |

See `getDefaultFieldSpec()` in `useDataBrowser.ts` for the complete list.
User-set values always win over smart defaults.

---

## What Was Removed

The previous architecture had a separate `views` layer:

```json
// OLD — removed
{
  "db": {
    "list": [...],
    "detail": [...],
    "views": [{ "name": "compact", "list": [...], "detail": [...] }]
  }
}
```

Views were an indirection layer that paired list and detail layouts by name.
The new structure eliminates this — each named layout declares its own pairings
directly. The data IS the view.

---

## Validation

**Backend:** `DbFieldSpec` and layout containers are Pydantic models with
`extra = 'forbid'`. Unknown keys are rejected.

**Frontend:** `toFieldSpecs()` in `useDataBrowser.ts` normalizes bare strings
to `DbFieldSpec` objects and applies smart defaults.

**Alice:** Validates layouts against this schema on save, import, and generation.

---

## For Alice

1. Every model gets one `workbench_fields` Setting with `config.layout`
2. `layout.list` = named dict of list layouts (grid columns)
3. `layout.detail` = named dict of detail layouts (admin field grid)
4. `layout.ui` = named dict of ui layouts (business forms)
5. `layout.active` = which named layout is currently selected per type
6. Each named layout declares its paired layouts in the other types
7. `field` must match a real model field — validate against the model's field list
8. `width` is in pixels, set by the user — don't override without asking
9. "default" always exists and is the fallback for broken pointers
10. Unknown keys in DbFieldSpec are rejected — don't invent new ones
