export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface KanbanTask {
  id: string;
  title: string;
  description?: string;
  priority: TaskPriority;
  assignee?: string;
  assigneeAvatarUrl?: string;
  dueDate?: string;
  tags?: string[];
  progress?: number;
}

export interface KanbanColumn {
  id: string;
  title: string;
  taskIds: string[];
  wipLimit?: number;
}

export interface BoardData {
  tasks: Record<string, KanbanTask>;
  columns: Record<string, KanbanColumn>;
  columnOrder: string[];
}
