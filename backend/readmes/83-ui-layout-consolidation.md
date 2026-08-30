# 83 — UI Layout Consolidation

**Date:** 2026-08-21
**Status:** Complete
**Session:** CSS fixes + detail view consolidation + console cleanup

---

## What Was Done

### 1. CSS Fixes — Kanban + Gantt Dark Theme

**Kanban** (`TaskCard.tsx:136`): Project name badge had `bg-indigo-100` with no dark variant. Added `dark:bg-indigo-500/20 dark:text-indigo-200`.

**Gantt** (`GanttTaskTemplate.tsx`): Task text color was hardcoded `#111827` — invisible on dark backgrounds. Changed to `color: inherit`. Bar container in `GanttTimeline.tsx` now sets `color: colors?.text` from the colorMap, which already computes readable text via `pickReadableTextColor()`.

### 2. Gantt Scaling Fix

**Problem:** CSS `zoom` on the DualScrollbar shrank everything uniformly — at 40%, text was 4.8px and unreadable.

**Fix:** Replaced CSS zoom with `cellWidth` scaling. `cellWidth={Math.round(40 * chartZoom)}` adjusts time density (pixels per day) while font size and row height stay constant. Removed counter-zoom hack on the list panel.

**Files changed:** `UnifiedGantt.tsx` (3 edits), `GanttTimeline.tsx` (1 edit), `GanttTaskTemplate.tsx` (3 edits)

### 3. Detail View Consolidation — 3 Files → 1

**Problem:** `ContactDetailJson.tsx` (335 lines), `OrgDetail.json.tsx` (375 lines), and `ItemDetailJson.tsx` (292 lines) were nearly identical — same state management, same handlers, same toolbar, same header rendering. Only differences: model name, tab list, tab-to-panel wiring.

**Solution:**

| New file | Purpose |
|----------|---------|
| `panelRegistry.tsx` | Maps tab content names → panel components. 19 panels registered. Default tab configs for 7 models. `registerPanel()` for runtime extension. |
| `ModelDetailPage.tsx` | Unified detail page (~240 lines). Reads layout JSON via `useDetailLayout`, renders header columns with `FieldRow`, renders tabs via panel registry. Works for any model. |

**Deleted:** ContactDetailJson.tsx, OrgDetail.json.tsx, ItemDetailJson.tsx (~1,000 lines removed)

**Updated routes:** Router.tsx, protectedRoutesConfig.tsx, wrapperPage.ts, dbRoutes.ts, WcapiRouteHandler.tsx, GetHelpDialog.tsx

**WcapiRouteHandler.tsx** was also cleaned — it imported from 7 dead files. Rewritten to use ModelDetailPage + UiDetail (94 → 42 lines).

### 4. Console Cleanup — UserActivityDashboard Removed

**Problem:** UserActivityDashboard (570 lines) showed API call statistics — system monitoring, not user activity. Real user activity is touches and actions, which AgendaView already shows.

**Fix:** Deleted UserActivityDashboard. Route `/core/user-activity` redirects to `/agenda`.

**AgendaView improvements:**
- Staff filter now works (was `// TODO`) — filters by `assigned_to`, `logged_by`, `contact_id`
- Single-select dropdown → multi-select chip bar (click to toggle, "All" to clear)
- Toolbar restructured: row 1 = title + badges, row 2 = staff filter chips (sticky)
- Content area scrolls independently
- All inline styles converted to Tailwind classes

---

## Layout Categories — Established

| Category | What it is | Examples |
|----------|-----------|---------|
| **databrowser** | List views | databrowser, OrgPage |
| **db.detail** | Detail views | ModelDetailPage, TransactionDetail (UiDetail) |
| **db.form** | Form views | DynamicDetail |
| **Cards** | Single record fields — floating or grouped data entry | DDCard, WarehouseCard, SpecCard, ShoppingCart |
| **Panels** | Lists of related records | ActionsPanel, DocumentsPanel, CommPanel, BomPanel |
| **Console** | Admin/monitoring | CommerceDashboard, InventoryDashboard, AliceDashboard |
| **Workspace** | Multi-pane work areas | AllModelsWorkbench |
| **Flight Simulator** | Step-by-step training | FlightSimConsole, ParadeOfReportsPage, FormParade |
| **Gantt** | Gantt chart | UnifiedGanttPage |
| **Kanban** | Kanban board | KanbanBoardPage |

**Card/Panel rule:** Cards show one record's fields. Panels list multiple records. Cards can contain Panels (embedded lists). Panels use Cards as row renderers. Naming convention enforces the distinction.

---

## Files Changed

| File | Action |
|------|--------|
| `src/components/common/panelRegistry.tsx` | Created — panel component registry |
| `src/components/common/ModelDetailPage.tsx` | Created — unified detail page |
| `src/apps/utils/kanban/TaskCard.tsx` | Fixed dark theme on project badge |
| `src/apps/utils/gantt/GanttTaskTemplate.tsx` | Fixed hardcoded text colors |
| `src/apps/utils/gantt/GanttTimeline.tsx` | Added `color` from colorMap to bar container |
| `src/apps/utils/gantt/UnifiedGantt.tsx` | Replaced CSS zoom with cellWidth scaling |
| `src/routes/Router.tsx` | Consolidated to ModelDetailPage |
| `src/routes/protectedRoutesConfig.tsx` | Consolidated to ModelDetailPage |
| `src/routes/WcapiRouteHandler.tsx` | Rewritten — dead imports removed |
| `src/pages/wrapperPage.ts` | Removed legacy aliases |
| `src/pages/admin/dbRoutes.ts` | All detail entries → ModelDetailPage |
| `src/pages/admin/AgendaView.tsx` | Staff chip bar, filter working, inline styles removed |
| `src/components/common/GetHelpDialog.tsx` | Updated component help |
| `src/apps/orgs/components/index.ts` | Removed OrgDetailJson export |

| File | Deleted |
|------|---------|
| `src/apps/core/models/contact/pages/ContactDetailJson.tsx` | 335 lines |
| `src/apps/orgs/components/OrgDetail.json.tsx` | 375 lines |
| `src/apps/products/pages/ItemDetailJson.tsx` | 292 lines |
| `src/pages/admin/UserActivityDashboard.tsx` | 570 lines |

**Net: ~1,572 lines deleted, ~480 lines added. 4 files deleted, 2 created.**
