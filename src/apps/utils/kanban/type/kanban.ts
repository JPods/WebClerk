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
  project_name?: string;
  assignee?: string;
  assignee_avatar_url?: string;
  dt_due?: string;
  dt_start?: string;
  dt_end?: string;
  dt_expected?: string;
  dt_completed?: string;
  dt_created?: string;
  dt_updated?: string;
  project_metadata?: any;
  created_by?: any;
  updated_by?: any;
  expected_by?: any;
  due_by?: any;
  completed_by?: any;
  start_by?: any;
  end_by?: any;
  tags?: string[];
  progress?: number;
  backend_id?: string;
  status?: string;
  language_codes?: string[];
  title_translations?: LocalizedTextMap;
  description_translations?: LocalizedTextMap;
  remarks?: string;
  priority_value?: number;
  difficulty?: number;
  linkage?: number;
  assigned_to?: KanbanAssignment[];
  dates?: Record<string, KanbanDateRecord | null | undefined>;
  children?: Array<{ id: string | number; name: string }>;
  sequence?: number;
  refs?: {
    links?: {
      parent?: string;
    };
    [key: string]: unknown;
  };
  project_id?: string | number;
  is_active?: boolean;
}

export interface KanbanColumn {
  id: string;
  title: string;
  task_ids: string[];
  wip_limit?: number;
}

export interface BoardData {
  tasks: Record<string, KanbanTask>;
  columns: Record<string, KanbanColumn>;
  column_order: string[];
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
