# WC List Selection Standard

**Established:** 2026-08-01
**Applies to:** All list/table views across the WC ecosystem — databrowser, Statement Sorter, any future list UI.

## The Rule

No checkboxes. The row is the selection target. Standard browser/OS behavior:

| Action | What it does |
|--------|-------------|
| **Click** | Selects that row. Clears all other selections. |
| **Shift+Click** | Range select — selects all rows between the last clicked row and this one (inclusive). Adds to existing selection. |
| **Cmd+Click** (Mac) / **Ctrl+Click** (Windows) | Toggle — adds or removes that individual row from the selection without affecting others. |
| **Select All** button | Adds all visible (non-filtered) rows to the selection. |
| **Clear Selection** button | Deselects everything. |

## Why No Checkboxes

- Checkboxes are tiny targets. The row is a much larger, easier target.
- This matches standard behavior in Finder, Windows Explorer, email clients, spreadsheets — every list interface users already know.
- Reduces visual clutter — no column consumed by checkboxes.
- Selection state is shown by row highlight (blue outline + background), not by a separate widget.

## Visual Feedback

- Selected rows get a distinct visual treatment: blue outline and highlighted background.
- A selection count appears in the toolbar: "N selected".
- Classification/status background colors are suppressed on selected rows so the selection highlight is unambiguous.

## Interaction with Inline Controls

Row clicks on `<select>`, `<input>`, or other interactive elements inside the row do NOT trigger selection. Only clicks on non-interactive areas (date, description, amount, source, bank_category) select.

## Implementation Reference

- **databrowser:** `React2025/src/components/common/DataGrid.tsx` lines 649-677
- **Statement Sorter:** `sites/statement_sorter/index.html` — `handleRowClick()`

## Bulk Actions on Selection

After selecting rows, toolbar buttons apply to the selection:
- "Selected → Business" / "Selected → Personal" / "Selected → Unknown"
- "Set Category..." dropdown
- Any future bulk action

If no rows are selected, bulk actions show a toast: "Select rows first".
