# Font Size Exceptions

Files and patterns where hardcoded `fontSize` / `font-size` values are
intentionally retained. Alice's code standards scanner (`hardcoded-font-size`
and `hardcoded-font-size-css`) excludes these so they don't appear as
violations.

Check this list before flagging a font-size violation — if it's listed here,
it was reviewed and accepted.

---

## TSX Exceptions

### ProjectGanttPanel.tsx
**Excluded from scanner.**

| Line | Value | Why |
|------|-------|-----|
| ~154 | `fontSize: 8` | "today" marker label on Gantt timeline — must fit in a 1px-wide marker column; scaling would make it unreadable or overflow |
| ~223 | `fontSize: 9` | Percent-complete label inside Gantt bar — bar height is fixed at ~20px; label must fit inside without clipping |

These are data visualization elements where the text occupies a physically
constrained space. Scaling them with the user's preference would break the
layout at larger sizes.

### DataGrid.tsx
**Excluded from scanner.**

DataGrid defines the `--dg-fs` CSS variable system. Its `fontSize` prop
drives all child sizing. Excluding it prevents false positives on the
variable-setting code.

### PrintDocumentLayout.tsx
**Excluded from scanner.**

Print layouts use fixed sizes to match physical paper dimensions. PDF output
requires absolute sizing — relative values would produce unpredictable print
results.

---

## CSS Exceptions

### Print CSS (`components/print/`, `print/`)
**Excluded from scanner.**

All print stylesheets use fixed px values for paper-accurate rendering.
Same reasoning as PrintDocumentLayout.tsx above.

---

## How to Add an Exception

1. Add the file to the `exclude_files` list in the rule definition
   (`code_standards.py`, `ANTI_PATTERNS` list)
2. Add a row to this file explaining **why** the hardcoded value is correct
3. The reason must be physical constraint, not convenience — "it looks fine"
   is not a reason; "the container is 20px tall and the text must fit" is

---

## Standard: How Font Size Should Work

All UI components should read the user's font size preference:

**TSX (inline styles):**
```tsx
import { getUI } from '@/utils/contactUI';
const active = getUI<string>('theme.active', 'dark');
const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);
// Then: fontSize: baseFontSize - 2  (not fontSize: 11)
```

**CSS (stylesheets):**
```css
.my-root { font-size: var(--my-fs, 13px); }
.my-child { font-size: calc(var(--my-fs, 13px) - 2px); }
```

The JS component sets `--my-fs` on the root element via inline style.
