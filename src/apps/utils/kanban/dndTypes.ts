/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export const DRAG_TYPE_TASK = "KANBAN_TASK" as const;

export interface DragItem {
  type: typeof DRAG_TYPE_TASK;
  taskId: string;
  sourceColumnId: string;
  index: number;
}

export interface DropResult {
  columnId: string;
  index: number;
  dropType?: "column" | "trash";
}
