# CSS Architecture — React2025

**Created:** 2026-08-12
**Rule:** No inline `style={{}}` — all styling via CSS classes and custom properties.

## The System

All components inherit theme colors from CSS custom properties set on `.db-root`
(defined in `DataBrowser.css`). Dark and light mode are handled by toggling
`data-theme="dark"` on `.db-root` — no JavaScript theme objects.

### Variable Reference

| Variable | Purpose | Light | Dark |
|----------|---------|-------|------|
| `--db-bg` | Page background | #f8f9fa | #1e1e1e |
| `--db-surface` | Card/panel background | #ffffff | #252526 |
| `--db-surface-alt` | Alternate surface | #f1f3f5 | #2d2d2d |
| `--db-border` | Primary border | #dee2e6 | #3c3c3c |
| `--db-border-light` | Subtle border | #e9ecef | #4d4d4d |
| `--db-text` | Primary text | #212529 | #d4d4d4 |
| `--db-text-muted` | Secondary text | #6c757d | #888 |
| `--db-text-dim` | Tertiary text | #adb5bd | #666 |
| `--db-accent` | Primary action color | #0d6efd | #9cdcfe |
| `--db-accent-green` | Success / select | #198754 | #4ec98c |
| `--db-accent-gold` | Warning / highlight | #fd7e14 | #e8c870 |
| `--db-accent-red` | Danger / error | #dc3545 | #e05252 |
| `--db-accent-purple` | Lookup / FK | #6f42c1 | #c8a8e8 |
| `--db-input-bg` | Input background | #ffffff | #2a2a2a |
| `--db-input-border` | Input border | #ced4da | #555 |
| `--db-row-hover` | Row hover | #f1f3f5 | #2a2d2e |
| `--db-row-active` | Selected row | #cfe2ff | #094771 |
| `--db-row-checked` | Multi-select row | #fff3cd | #3a3a1a |
| `--db-resize-handle` | Column resize | #0d6efd | #4a9eff |
| `--db-btn-bg` | Button background | #ffffff | #2d2d2d |
| `--db-btn-primary` | Primary button | #0d6efd | #0e639c |
| `--db-btn-save` | Save button | #198754 | #1a6b2e |
| `--db-btn-danger` | Danger button | #dc3545 | #6b1a1a |

## File Structure

Each component gets its own CSS file, imported at the top of the `.tsx`:

```
components/
  fields/
    fields.css          ← field widgets (.db-label, .db-input, .db-field)
  common/
    DataGrid.css        ← .dg-* classes
    GetHelpDialog.css   ← .gh-* classes
    ReportsDialog.css   ← .rd-* classes
    FieldOrderDialog.css ← .fo-* classes
    DedupPanel.css      ← .dp-* classes
    ParadeOfReports.css ← .por-* classes
    DetailLayoutDialog.css ← .dld-* classes
    BarnCleaner.css     ← .bc-* classes
  print/
    PrintLayoutDesigner.css ← .pld-* classes
    SectionCard.css     ← .sc-* classes
pages/admin/
    DataBrowser.css     ← .db-* variables + .db-root styles
```

## Naming Convention

Each component uses a **unique short prefix** to prevent collisions:

| Prefix | Component |
|--------|-----------|
| `db-` | DataBrowser (variables + shared classes) |
| `dg-` | DataGrid |
| `gh-` | GetHelpDialog |
| `rd-` | ReportsDialog |
| `fo-` | FieldOrderDialog |
| `dp-` | DedupPanel |
| `por-` | ParadeOfReports |
| `dld-` | DetailLayoutDialog |
| `bc-` | BarnCleaner |
| `pld-` | PrintLayoutDesigner |
| `sc-` | SectionCard |

Pattern: `{prefix}-{element}--{modifier}`

```css
.dg-row              /* element */
.dg-row--checked     /* modifier */
.dg-row--striped     /* modifier */
.dg-toolbar-btn      /* sub-element */
.dg-toolbar-btn--active-blue  /* sub-element modifier */
```

## Dynamic Font Sizes

Components that accept a `fontSize` prop set CSS custom properties on their root
element. All child elements reference these instead of inline fontSize values:

```tsx
<div className="dg-root" style={{
  '--dg-fs': `${fontSize}px`,
  '--dg-fs-sm': `${fontSize - 1}px`,
  '--dg-fs-xs': `${fontSize - 2}px`,
} as React.CSSProperties}>
```

```css
.dg-th { font-size: var(--dg-fs-sm, 12px); }
.dg-toolbar-btn { font-size: var(--dg-fs-xs, 11px); }
```

This is the **one legitimate use of inline style** — setting CSS custom properties
from props. The actual font-size values live in CSS.

## When Inline Styles Are Allowed

Inline `style={{}}` is only acceptable for values that are **computed from data at
runtime** and cannot be expressed as CSS classes. Every instance must be justified.

### Current Exceptions (29 total, as of 2026-08-12)

**CSS custom property injection** (font-size props → CSS vars):
- `DataGrid.tsx:928` — `--dg-fs`, `--dg-fs-sm`, `--dg-fs-xs` from `fontSize` prop
- `DedupPanel.tsx:188` — `--dp-fs` from `fontScale` state
- `PrintLayoutDesigner.tsx:429` — `--pld-fs` from `fontSize` prop

**Computed layout dimensions** (from user interaction or data):
- `DataGrid.tsx:952` — table `width` from sum of column widths
- `DataGrid.tsx:963` — header cell `width`/`minWidth` per column from `colWidths`
- `DataGrid.tsx:812` — body cell `width`/`minWidth`/`textAlign`/`paddingLeft` per column
- `DataGrid.tsx:930` — `cursor: grab` when table overflows container
- `PrintLayoutDesigner.tsx:466,613` — panel `flex: 0 0 ${midWidth}px` from drag-resize
- `PrintLayoutDesigner.tsx:593` — preview iframe `width`/`height` from paper size
- `SectionCard.tsx:167-349` — 9 input `width` values (field-specific fixed widths)

**Data-driven colors** (per-record or per-category, not themeable):
- `DataGrid.tsx:1125` — context menu `left`/`top` from click coordinates
- `ReportsDialog.tsx:454` — badge `background` from `categoryColor()` per report
- `FieldOrderDialog.tsx:504` — behavior badge `color`/`border`/`background` from field type
- `PrintLayoutDesigner.tsx:482,517,520,522` — section type `color`/`background` from `SECTION_META`
- `SectionCard.tsx:373,391` — section `borderLeftColor` and badge `background` from type

**Computed spacing** (depth-dependent):
- `FieldOrderDialog.tsx:562` — `paddingLeft` computed from JSON tree `depth * 16`

### Not Allowed

- Colors → use `--db-*` variables
- Font sizes → use component CSS vars (`--dg-fs`, etc.)
- Spacing, padding, margin → use CSS classes
- Borders, border-radius → use CSS classes
- Hover effects → use CSS `:hover`, never `onMouseEnter`/`onMouseLeave`
- Theme objects (`t.accent`, `th.text`, `DEFAULT_THEME`) → removed; use CSS vars

## How to Add a New Component

1. Create `ComponentName.css` alongside the `.tsx`
2. Pick a unique 2-4 letter prefix (check the table above)
3. Import the CSS file: `import './ComponentName.css'`
4. Use `--db-*` variables for all colors
5. If the component accepts `fontSize`, set `--{prefix}-fs` on the root element
6. Use `var(--db-variable, fallback)` with sensible fallbacks for standalone use
7. Zero inline styles unless the value is computed from data at runtime

## Field Widgets

The `components/fields/` directory contains reusable field widgets with a shared
contract (`FieldWidgetProps` in `types.ts`). All styling uses `.db-*` classes from
`fields.css`.

- `renderField(name, value, behavior, onChange, opts)` — dynamic dispatch from behavior config
- `getWidget(typeName)` — returns the component for a type name
- `BaseField` — shared wrapper with label, error display, Shift-for-Help
- 20 widget types registered: text, number, currency, email, phone, url, address,
  select, lookup, boolean, date, timestamp, json, json-tree, textarea, readonly,
  geo, zip, masked, hidden

`BehaviorField` is a thin dispatcher that calls `renderField()`. It exists for
backward compatibility with DataBrowser — new code should use `renderField()` or
individual widget components directly.

## For Alice

When Alice evaluates UI changes or flags patterns:

1. Any `style={{}}` in a PR that isn't on the exceptions list above is a defect
2. Any new `onMouseEnter`/`onMouseLeave` for hover styling is a defect — use CSS `:hover`
3. Any JS theme object (`const theme = { ... }`) being passed as props is a defect
4. New components without a CSS file and unique prefix are incomplete
5. Colors hardcoded in JSX (not via `--db-*` vars) break dark mode
