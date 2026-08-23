/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */

export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface LocalizedTextMap {
  [languageCode: string]: string;
}

export interface KanbanRefId {
  id: number | string;
}

export interface KanbanDateRecord {
  dt: number | string | null;
  who: KanbanRefId | null;
}

export interface KanbanTask {
  id: string;
  uuid?: string;
  ida?: string;
  properties?: {
    action: LocalizedTextMap;
    description?: LocalizedTextMap;
    assigned_to?: KanbanRefId[];
    languages?: string[];
    status?: string;
    priority?: number;
    difficulty?: number;
    percent_complete?: number;
    burndown?: number;
    dates?: Record<string, KanbanDateRecord | null | undefined>;
    remarks?: string;
    linkage?: number;
    sequence?: number;
    kanban_column?: string;
  };
  project_id?: number | string;
  project_name?: string;
  assignee?: string;
  assignee_avatar_url?: string;
  assigned_to?: KanbanRefId[] | string[];
  refs?: {
    links?: {
      parent?: number | string;
    };
    [key: string]: unknown;
  };
  dt_created?: number;
  dt_modified?: number;
  dt_updated?: number | string | null;
  dt_start?: number | string | null;
  dt_expected?: number | string | null;
  dt_deadline?: number | string | null;
  dt_completed?: number | string | null;
  duration?: number | null;
  created_by?: unknown;
  updated_by?: unknown;
  expected_by?: unknown;
  due_by?: unknown;
  completed_by?: unknown;
  start_by?: unknown;
  end_by?: unknown;
  project_metadata?: unknown;
  tags?: string[];
  percent_complete?: number;
  backend_id?: string;
  status?: string;
  language_codes?: string[];
  title_translations?: LocalizedTextMap;
  description_translations?: LocalizedTextMap;
  remarks?: string;
  title?: string;
  description?: string;
  priority?: number | TaskPriority;
  difficulty?: number;
  priority_value?: number;
  linkage?: number;
  sequence?: number;
  is_active?: boolean;
  attachments?: Array<{
    id: number;
    name: string;
    size_bytes: number;
    mime_type: string;
    url?: string;
  }>;
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
    assigned_to: KanbanRefId[];
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
  assigned_to?: KanbanRefId[];
  linkage?: number;
  remarks?: string;
  dt_start?: string | null;
  dt_expected?: string | null;
  dt_deadline?: string | null;
  dt_completed?: string | null;
  assignee?: string;
}

export interface UpdateKanbanTaskStatusRequest {
  status: string;
  columnId?: string;
  priority?: number;
  difficulty?: number;
  remarks?: string;
}
