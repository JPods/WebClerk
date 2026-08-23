# Report Editor Types — Plain, Markdown, HTML

**Established:** 2026-08-12
**Migration:** core 0039
**Applies to:** All WC3 Report records with user-authored content

---

## Two New Fields on Report

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `editor_type` | CharField (choices) | `plain` | Which editor the frontend renders for the content field |
| `content` | TextField | `""` | Report body template — interpreted according to editor_type |

### editor_type choices

| Value | Frontend editor | Backend rendering | Use case |
|-------|----------------|-------------------|----------|
| `plain` | Textarea (12 rows) | `<pre>` with preserved whitespace | Scripts, raw text, simple notes |
| `markdown` | @uiw/react-md-editor with edit/preview toggle | Python `markdown` library → HTML | Internal notes, documentation, {{token}} preview |
| `svg` | PrintLayoutDesigner (Export/Import SVG) | SVG populate (resolve IDs → data) | Designed print forms — invoices, POs, proposals |

**Removed:** `html` (TinyMCE). WC3 is not an email or letter formatting tool. Users have Gmail, Word, Pages — WC3 provides `{{token}}` fields and data export. Users copy tokens into their own programs.

---

## Relationship to Script Fields

The `content` field is the **document template** — what the report looks like.
The `script_before`, `script_during`, `script_after` fields are **computation logic** — what the report calculates.

A report can have both: scripts compute the data, content provides the layout.
A report can have just content (static letter) or just scripts (data export) or neither (built-in template like Invoice).

```
┌─────────────────────────────────────────────┐
│  Report Record                              │
│                                             │
│  editor_type ──► selects frontend editor    │
│  content     ──► document body template     │
│                                             │
│  script_before ──┐                          │
│  script_during ──┼──► computation pipeline  │
│  script_after  ──┘    (see report-script-   │
│                        pipeline.md)         │
└─────────────────────────────────────────────┘
```

---

## Frontend Architecture

### EditorField Component

`react-joint/src/components/fields/EditorField.tsx`

A reusable field widget that switches editor based on its `editorType` prop:

- Registered as `editor` in the widget registry (`components/fields/index.tsx`)
- Added to `AdminFieldKind` type (`apps/utils/3column/types.ts`)
- All three sub-editors (plain, markdown, TinyMCE) are **lazy-loaded** — no bundle cost until used

### Where it renders

| Context | How it works |
|---------|-------------|
| **ReportDetail.tsx** | Editor Type dropdown + EditorField reads `watch("editor_type")` to switch live |
| **ReportDisplay.tsx** | Detects `content` field, renders EditorField with record's `editor_type` |
| **DataBrowser (3-column)** | `RecordDetailColumn.tsx` handles `kind: "editor"` — reads sibling `editor_type` from `formValues` |

### npm packages

- `@uiw/react-md-editor` — Markdown editor with preview

**Not installed (by design):** TinyMCE. WC3 does not format emails or letters. Users copy `{{tokens}}` into Gmail, Word, Pages, or any tool they prefer. WC3 exports data in formats those tools consume.

---

## Backend Rendering

`apps/core/services/report_renderer.py` — `_render_content_report()`

When a Report has non-empty `content`, the renderer uses it instead of built-in templates:

| editor_type | Conversion | Result |
|-------------|-----------|--------|
| `plain` | Wrapped in `<pre>` | Whitespace-preserved plain text |
| `markdown` | `markdown.markdown()` with tables + fenced_code extensions | Styled HTML |

Both are wrapped in the standard page template (`_BASE_CSS` + company header) for internal rendering. For customer-facing output, users copy resolved tokens into their own tools.

### Python dependency

`markdown` (pip) — installed in WC3 venv. Used only by the renderer; graceful fallback to `<pre>` if not available.

---

## Field Behaviors (seed_field_access.py)

The seeder maps these fields for the databrowser:

| Field | Behavior type | Widget |
|-------|--------------|--------|
| `editor_type` | `select` (inline options) | Dropdown: Plain text / Markdown / HTML |
| `content` | `editor` | EditorField — switches on sibling editor_type |

Run `python manage.py seed_field_access` after migration to populate.

---

## Priority of content sources

When `render_report()` is called, it checks in order:

1. **Report.content** (non-empty) → `_render_content_report()` using editor_type
2. **Built-in template** (template_key matches _TEMPLATE_MAP) → Invoice, Pick List, etc.
3. **Generic fallback** → auto-generated table from model fields

User-authored content takes precedence over built-in templates. This means a report can override a built-in template by adding content — useful for customized versions of standard documents.
