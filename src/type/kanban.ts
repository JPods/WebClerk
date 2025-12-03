export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface LocalizedTextMap {
  [languageCode: string]: string;
}

export interface KanbanAssignment {
  id: string;
  name: string;
}

export interface KanbanDateRecord {
  dt: string;
  who: KanbanAssignment;
}

export interface KanbanTask {
  id: string;
  title: string;
  description?: string;
  priority: TaskPriority;
  assignee?: string;
  assigneeAvatarUrl?: string;
  dueDate?: string;
  startDate?: string;
  endDate?: string;
  tags?: string[];
  progress?: number;
  backendId?: string;
  status?: string;
  languageCodes?: string[];
  titleTranslations?: LocalizedTextMap;
  descriptionTranslations?: LocalizedTextMap;
  remarks?: string;
  priorityValue?: number;
  difficulty?: number;
  linkage?: number;
  assignedTo?: KanbanAssignment[];
  dates?: Record<string, KanbanDateRecord | null | undefined>;
  children?: Array<{ id: string | number; name: string }>;
  sequence?: number;
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

export interface KanbanApiTask {
  id: string;
  parent: {
    id: string;
    zzz?: string;
  };
  properties: {
    lang: string[];
    action: LocalizedTextMap;
    status: string;
    priority: number;
    difficulty: number;
    dates: Record<string, KanbanDateRecord | null | undefined>;
    assigned_to: KanbanAssignment[];
    linkage?: number;
    description: LocalizedTextMap;
    children?: Array<{ id: number | string; name: string }>;
    remarks?: string;
  };
}

export interface CreateKanbanTaskRequest {
  parentId: string;
  lang: string[];
  action: LocalizedTextMap;
  description: LocalizedTextMap;
  status: string;
  priority: number;
  difficulty: number;
  dates?: Record<string, KanbanDateRecord | null | undefined>;
  assigned_to?: KanbanAssignment[];
  linkage?: number;
  remarks?: string;
  dueDate?: string;
  assignee?: string;
}

export interface UpdateKanbanTaskStatusRequest {
  status: string;
  columnId?: string;
  priority?: number;
  difficulty?: number;
  remarks?: string;
}
