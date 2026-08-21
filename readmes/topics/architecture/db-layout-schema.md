# DataBrowser Layout Schema

**Location:** `common/schemas/setting.py`
**Stored on:** Setting records with `purpose='wc:model'`
**Path:** `config.layout.*`
**Terms established:** 2026-08-18 — team decision, fixed for the life of the project.

---

## The Four Layout Types

Every model's layout lives in one Setting record (`purpose='wc:model'`). Four
paired types — each named layout declares which layouts it pairs with in the
other types. Pick any one, the others follow.

| Key | Class | What it is | Why this name |
|---|---|---|---|
| `layout.list` | `NamedListLayout` | Grid of many records | Universal term |
| `layout.detail` | `NamedDetailLayout` | All fields, one record, collapsible groups | You click a list row, you see the *detail* |
| `layout.form` | `NamedFormLayout` | Curated business form — cards, tabs, lines | Users fill out *forms* — invoices, orders, contacts |
| `layout.column` | `NamedColumnLayout` | Panel grid inside a detail view | Describes the rendering shape |

Two unpaired types exist alongside:

| Key | What it is |
|---|---|
| `layout.panel` | Panel field specs — always rendered in context, not paired |
| `layout.card` | Named card definitions — reusable blocks of fields, referenced by form layouts |

### The Admin/App Toggle

The DataBrowser top bar toggles between **Admin** and **App** mode for the right panel:

- **Admin mode** → renders the active **detail** layout (GroupedDetailFields — all fields, collapsible groups)
- **App mode** → renders the active **form** layout (DynamicDetail or *DetailJson — curated business form)

The **list** always controls the left panel regardless of mode.

---

## Layout Structure

```json
{
  "layout": {
    "active": {
      "list": "default",
      "detail": "default",
      "form": "default",
      "column": "default"
    },
    "list": {
      "default": {
        "detail": "default",
        "form": "default",
        "columns": [
          { "field": "ida", "width": 100, "align": "left" },
          { "field": "name", "width": 180 },
          { "field": "status", "width": 80, "align": "center" }
        ]
      },
      "bill_layout": {
        "detail": "compact",
        "form": "default",
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
        "form": "default",
        "fields": [
          { "field": "name", "width": 200 },
          { "field": "scope", "width": 100 },
          { "field": "config" }
        ]
      },
      "compact": {
        "list": "bill_layout",
        "form": "default",
        "fields": [
          { "field": "name", "width": 200 },
          { "field": "status" }
        ]
      }
    },
    "form": {
      "default": {
        "list": "default",
        "detail": "default",
        "header": {
          "layout": "columns",
          "cards": ["identity", "status"]
        },
        "lines": {
          "family": "sell",
          "toolbar": ["add", "delete"],
          "actions": ["fulfill", "invoice"]
        },
        "tabs": [
          { "label": "Summary", "content": "summary" },
          { "label": "Actions", "content": "actions" },
          { "label": "Documents", "content": "documents" }
        ],
        "edit_rules": {
          "locked_statuses": ["released", "void"],
          "status_field": "status",
          "require_unlock_for": ["price", "qty"]
        }
      }
    },
    "column": {
      "default": {
        "detail": "default",
        "form": "default",
        "columns": [
          { "field": "ida", "width": 100 },
          { "field": "name", "width": 180 }
        ]
      }
    },
    "panel": [
      { "field": "ida", "width": 80 },
      { "field": "name", "width": 160 }
    ],
    "card": {
      "identity": {
        "title": "Identity",
        "title_ida": "customer_id",
        "fields": [
          { "field": "company" },
          { "field": "display_name" },
          { "field": "email", "type": "readonly" }
        ]
      },
      "status": {
        "title": "Status",
        "component": "StatusCard",
        "fields": [
          { "field": "status", "type": "select", "options": ["draft", "open", "closed"] }
        ]
      }
    },
    "related": ["action", "document", "communication"]
  }
}
```

### How Pairing Works

1. **`active`** tracks which named layout is currently selected for each type.
   On load, read `active` and render accordingly.

2. **Pick any layout — the other three follow.** Switch list to "bill_layout" and
   detail flips to "compact", form stays "default" (because that's what bill_layout declares).

3. **Pairings are independent, not bidirectionally enforced.** List "bill_layout"
   says `detail: "compact"`. Detail "compact" says `list: "default"`. That's fine —
   each entry point is its own opinion. If you force bidirectional consistency
   you're back to a views layer. The asymmetry is a feature.

4. **"default" always exists, always the fallback.** If a layout points to a name
   that doesn't exist, fall back to "default" silently. "default" can be edited
   but never deleted.

---

## DbFieldSpec

Every item in a list/detail/column `columns` or `fields` array is a `DbFieldSpec`:

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

## CardFieldSpec

Fields inside a card definition (used by form layouts):

```json
{
  "field": "company",
  "label": "Company Name",
  "type": "readonly",
  "options": null,
  "help": "Legal entity name"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `field` | string | required | Model field name |
| `label` | string or null | null | Override display label |
| `type` | string or null | null | Widget override: select, readonly, editable, search, action |
| `options` | string[] or null | null | For select fields |
| `help` | string or null | null | Shift+hover tooltip text |

## CardSpec

A reusable card definition — named block of fields with optional component override.
Cards are the building blocks of form layouts. Most cards are pure JSON (fields
rendered via FieldRow). Cards that need interactive behavior reference a registered
React component by name.

```json
{
  "title": "Identity",
  "title_ida": "customer_id",
  "component": null,
  "footer": null,
  "source": "config.billing",
  "fields": [...]
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | string | required | Card heading |
| `title_ida` | string or null | null | Field name for ID badge next to title |
| `component` | string or null | null | Registered React component name (overrides field rendering) |
| `footer` | string or null | null | Registered footer component name |
| `source` | string or null | null | Dot-path prefix for all fields in this card |
| `fields` | CardFieldSpec[] | [] | Fields to render |

---

## Form Layout Sections

A form layout (`NamedFormLayout`) is the richest layout type. It drives the
full detail page in App mode — header cards, line items, tabs, and edit rules.

### Header

Arranges cards at the top of the form:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `layout` | string | "columns" | Arrangement: columns, rows, stacked |
| `cards` | string[] | [] | Card names from `layout.card` |

### Lines

Line items section (order lines, invoice lines, etc.):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `family` | string or null | null | Line family: sell, exec |
| `toolbar` | string[] | [] | Toolbar actions |
| `actions` | string[] | [] | Line-level actions |

### Tabs

Tabbed sections below the header and lines:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `label` | string | required | Tab label |
| `content` | string | required | Panel name: summary, actions, documents, etc. |

### Edit Rules

Controls when fields are locked:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `locked_statuses` | string[] | [] | Statuses that lock the form |
| `status_field` | string | "status" | Which field controls locking |
| `require_unlock_for` | string[] | [] | Fields that require explicit unlock |

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

## Where It Lives

```
Setting (one per model)
  purpose: "wc:model"
  parent_model: "contact"  (or "order", "item", etc.)
  config:
    layout:
      active: { list: "default", detail: "default", form: "default", column: "default" }
      list:
        default: { detail: "default", form: "default", columns: [...] }
      detail:
        default: { list: "default", form: "default", fields: [...] }
      form:
        default: { list: "default", detail: "default", header: {...}, lines: {...}, tabs: [...], edit_rules: {...} }
      column:
        default: { detail: "default", form: "default", columns: [...] }
      panel: [...]
      card: { identity: {...}, status: {...} }
      related: ["action", "document"]
```

One Setting record per model. One source of truth.

---

## Rendering Stack

```
Setting (config.layout)        ← JSON layout definition, syncable, per-user overridable
    ↓
useDataBrowser hook            ← loads Setting, resolves active layouts, computes field specs
    ↓
DataBrowser.tsx                ← left panel (list), right panel (detail or form)
    ↓ (Admin mode)                              ↓ (App mode)
GroupedDetailFields            ← detail layout   DynamicDetail / *DetailJson  ← form layout
    ↓                                           ↓
FieldGroupSection              ← collapsible     Cards + Lines + Tabs
    ↓                                           ↓
BehaviorField                  ← field-level rendering based on field_behaviors
    ↓
Widget Registry (20 widgets)   ← text, select, date, currency, lookup, json-tree, etc.
```

---

## What Was Removed

The previous architecture had a separate `views` layer and used different names:

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

And a transitional naming that used `dynamic` (now `detail`) and `display` (now `form`).
Both are superseded by the terms established 2026-08-18.

---

## Validation

**Backend:** `DbFieldSpec`, `CardFieldSpec`, `CardSpec`, and all layout containers are
Pydantic models. `DbFieldSpec` uses `extra = 'forbid'` — unknown keys are rejected.
Form-related schemas use `extra = 'allow'` to accommodate diverse content.

**Frontend:** `namedLayoutToWorkbench()` in `useDataBrowser.ts` normalizes named layouts
to the internal `WorkbenchFieldsSetting` format. `toFieldSpecs()` normalizes bare strings
to `DbFieldSpec` objects and applies smart defaults.

**Alice:** Validates layouts against this schema on save, import, and generation.

---

## For Alice

1. Every model gets one `wc:model` Setting with `config.layout`
2. `layout.list` = named dict of list layouts (grid columns)
3. `layout.detail` = named dict of detail layouts (admin field grid — all fields, groups)
4. `layout.form` = named dict of form layouts (business forms — cards, tabs, lines, edit rules)
5. `layout.column` = named dict of column layouts (panel grids inside detail views)
6. `layout.active` = which named layout is currently selected per type
7. Each named layout declares its paired layouts in the other types
8. `field` must match a real model field — validate against the model's field list
9. `width` is in pixels, set by the user — don't override without asking
10. "default" always exists and is the fallback for broken pointers
11. Unknown keys in DbFieldSpec are rejected — don't invent new ones
12. **Terms are fixed:** list, detail, form, column. Do not use dynamic, display, ui, or json as layout type names.
