# WC3 ↔ R25 Alignment Execution Plan

This document outlines the exact steps required to fully align R25 Kanban + Gantt with the WC3 Action/BaseModel schema.

The goal is:
- Replace dt_end with dt_completed everywhere
- Enforce canonical WC3 fields: dt_start, dt_expected, dt_deadline, dt_completed
- Update interfaces, forms, mappers, UI, and internal logic

---

## STEP 1 — Update TypeScript Types (BEST FIRST STEP)
- Update all kanban and gantt interfaces to remove dt_end
- Add dt_completed
- Ensure dt_start, dt_expected, dt_deadline all exist

Files:
- src/apps/utils/kanban/kanbanDataMapper.ts
- src/apps/utils/gantt/ganttDataMapper.ts
- src/type/kanban.ts (if present)

---

## STEP 2 — Update API Mappers (SECOND STEP)
Replace:
- dt_end → dt_completed
Map incoming WC3 fields directly into TS objects.

Ensure outgoing updates (PATCH payloads) use:
- dt_completed
- dt_deadline
- dt_expected
- dt_start

Files:
- kanbanDataMapper.ts
- ganttDataMapper.ts

---

## STEP 3 — Update Kanban UI (THIRD STEP)
Replace all references to dt_end with dt_completed:
- KanbanTaskModal
- KanbanActionEdit
- KanbanBoardPage (logic around due/start relationships)

Add expected date where appropriate:
- dt_expected (optional UI display)

---

## STEP 4 — Update Gantt UI (FOURTH STEP)
Gantt uses dt_end heavily. Replace hierarchy:
- END = dt_completed → dt_deadline → fallback
- START = dt_start → dt_expected → fallback

Files:
- GanttActionModal
- SvarGanttPage
- MultiProjectGanttPage
- GanttPage
- KanbanGanttPage

---
## STEP 4B — Dedicated Gantt Implementation Plan
Normalize Gantt to canonical WC3 fields.

1. Normalize model
- Use dt_start, dt_expected, dt_deadline, dt_completed
- Remove dt_end

2. Update mappers
- Convert dt_end → dt_completed
- start = dt_start || dt_expected
- end = dt_completed || dt_deadline || dt_expected

3. Update modals
- Update [`GanttActionModal.tsx`](src/apps/utils/gantt/GanttActionModal.tsx)

4. Update views
- [`GanttPage.tsx`](src/apps/utils/gantt/GanttPage.tsx)
- [`KanbanGanttPage.tsx`](src/apps/utils/gantt/KanbanGanttPage.tsx)
- [`MultiProjectGanttPage.tsx`](src/apps/utils/gantt/MultiProjectGanttPage.tsx)
- [`SvarGanttPage.tsx`](src/apps/utils/gantt/SvarGanttPage.tsx)

5. Timeline rendering
- dt_start primary start
- dt_completed primary end
- dt_deadline = deadline visual
- dt_expected = predictive

6. Interaction logic
- Drag/resize updates dt_start/dt_completed

7. Dependency lines update to WC3 fields

8. Regression tests for scaling, overlaps, drag/edit, deadlines

---

## STEP 4C — Current Gantt Codebase Targets
The following files under [`src/apps/utils/gantt`](src/apps/utils/gantt) require full WC3 schema alignment:

### Primary UI Entry Points
- [`MultiProjectGanttPage.tsx`](src/apps/utils/gantt/MultiProjectGanttPage.tsx)
- [`GanttPage.tsx`](src/apps/utils/gantt/GanttPage.tsx)
- [`SvarGanttPage.tsx`](src/apps/utils/gantt/SvarGanttPage.tsx)
- [`KanbanGanttPage.tsx`](src/apps/utils/gantt/KanbanGanttPage.tsx)

### Modals and Editors
- [`GanttActionModal.tsx`](src/apps/utils/gantt/GanttActionModal.tsx)

### Requirements
- All components must exclusively use WC3 fields:
  - dt_start
  - dt_expected
  - dt_deadline
  - dt_completed
- Remove all uses of deprecated dt_end
- Ensure all timeline, dragging, and resizing logic reads/writes only WC3-compliant fields
- Ensure Multi‑Project view uses canonical fields consistently across merged datasets

These files will be updated in sequence after mapper normalization.

---

## STEP 5 — Update Filters, Summaries, and Calculations (FIFTH STEP)
- Any calculation using dt_end must switch to dt_completed
- Any sorting, grouping, or date span logic must be updated

---

## STEP 6 — Documentation Cleanup (FINAL STEP)
Ensure all team members use the canonical WC3 field set:
- dt_start = actual start
- dt_expected = expected end
- dt_deadline = committed deadline
- dt_completed = actual completion

---

## 7. Remove dt_end References
All remaining references should be deleted.

Search pattern:
```
dt_end
```

---

## 8. Regression Testing
- Drag-drop in Kanban
- Gantt timeline scaling
- Task completion flows
- Due date warnings

---

## 9. Backward Compatibility
Incoming API payloads may still send dt_end.
Mapper should translate:
- If dt_completed missing and dt_end exists → dt_completed = dt_end

---

## Summary
Once this plan is confirmed, code modifications will begin in the precise order above.
