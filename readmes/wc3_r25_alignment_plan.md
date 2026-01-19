# WC3 ↔ R25 Alignment Execution Plan

This document outlines the exact steps required to fully align R25 Kanban + Gantt with the WC3 Action/BaseModel schema.

The goal is:
- Replace dt_end with dt_completed everywhere
- Enforce canonical WC3 fields: dt_start, dt_expected, dt_due, dt_completed
- Update interfaces, forms, mappers, UI, and internal logic

---

## STEP 1 — Update TypeScript Types (BEST FIRST STEP)
- Update all kanban and gantt interfaces to remove dt_end
- Add dt_completed
- Ensure dt_start, dt_expected, dt_due all exist

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
- dt_due
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
- END = dt_completed → dt_due → fallback
- START = dt_start → dt_expected → fallback

Files:
- GanttActionModal
- SvarGanttPage
- MultiProjectGanttPage
- GanttPage
- KanbanGanttPage

---

## STEP 5 — Update Filters, Summaries, and Calculations (FIFTH STEP)
- Any calculation using dt_end must switch to dt_completed
- Any sorting, grouping, or date span logic must be updated

---

## STEP 6 — Documentation Cleanup (FINAL STEP)
Ensure all team members use the canonical WC3 field set:
- dt_start = actual start
- dt_expected = expected end
- dt_due = committed deadline
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
