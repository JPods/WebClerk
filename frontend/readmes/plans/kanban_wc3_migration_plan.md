KANBAN WC3‑ALIGNED REFACTOR PLAN
Domain: kanban
Scope: utils, types, components only

NEW DIRECTORY LAYOUT
src/apps/core/models/kanban/
  index.ts
  types/
  utils/
  components/
  pages/

FILE MAPPING
dndTypes.ts -> types/dndTypes.ts
KanbanActionEdit.tsx -> pages/KanbanActionEdit.tsx
KanbanBoardDataPage.tsx -> pages/KanbanBoardDataPage.tsx
KanbanBoardPage.tsx -> pages/KanbanBoardPage.tsx
KanbanColumn.tsx -> components/KanbanColumn.tsx
KanbanDragLayer.tsx -> components/KanbanDragLayer.tsx
KanbanTaskModal.tsx -> pages/KanbanTaskModal.tsx
ProjectContactManager.tsx -> utils/ProjectContactManager.tsx
TaskCard.tsx -> components/TaskCard.tsx
taskFormTypes.ts -> types/taskFormTypes.ts
kanban.ts -> types/kanban.ts
kanbanDataMapper.ts -> utils/kanbanDataMapper.ts
junk.txt -> remove

CONSTRAINTS
No renaming exports unless needed
Maintain wc3 domain-model rules
Update imports after move
