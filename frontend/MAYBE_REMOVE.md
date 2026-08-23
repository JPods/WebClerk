# React2025 — Maybe Remove List

Items kept for now but may be dead. Review before next release.

| Item | Type | Why it might be dead | Why it might be needed |
|------|------|---------------------|----------------------|
| `flatpickr` (npm) | dependency | Only used by `date-picker.tsx` which nothing imports | Could be wired in later for a richer date picker than native `<input type="date">` |
| `react-apexcharts` + `apexcharts` (npm) | dependency | Only used by `LineChartOne.tsx` and `BarChartOne.tsx` (now deleted) | Commerce dashboard or reporting might want charts |
| `react-data-table-component` (npm) | dependency | Aliased in vite.config.ts to `reorderable-data-table.tsx`; used by `RecordListColumn.tsx` (3-column layout) | 3-column layout is live in routes |
| `src/lib/reorderable-data-table.tsx` | file | Vite alias wrapper for react-data-table-component | Same — 3-column layout depends on it |
| `src/components/common/FilterSelect.tsx` | component | No imports found | Could be useful for future filter UIs |
| `src/components/common/EmptyState.tsx` | component | No imports found | Generic "no data" display — might want it |
| `src/components/common/LoadingSpinner.tsx` | component | No imports found | Generic spinner — pages use inline spinners instead |
| `src/components/common/TransactionTabs.tsx` | component | No imports found | Transaction detail pages might use it |
| `src/components/common/ChartTab.tsx` | component | No imports found | Dashboard charting |
| `src/components/common/ConfirmDialog.tsx` | component | No imports found | Delete confirmations — might need it |
| `src/components/header/SaveQueueIndicator.tsx` | component | No imports found | Save queue exists (SaveQueueContext) — indicator might be re-added |
| `src/components/PermissionGuards.tsx` | component | No imports found | RBAC UI guards — might need for role-based feature hiding |
| `src/components/form/input/FileInput.tsx` | component | No imports found | Document upload feature will need this |
| `NotionTrackerPage.tsx` | page | Only page using FullCalendar (now uninstalled) | Will break if someone navigates to `/notion-tracker` |

**Rule:** If still unused at next Wednesday scrub, delete.
