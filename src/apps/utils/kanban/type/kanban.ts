// Add TaskPriority type for compatibility with string-based priorities
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';
export interface LocalizedTextMap {
  [languageCode: string]: string;
}

export interface KanbanRefId {
  id: number | string;
}

export interface KanbanDateRecord {
  dt: number | null;
  who: KanbanRefId | null;
}

export interface KanbanTask {
  // WC3 authoritative identity fields only
  id: string; // authoritative WC3 id
  uuid?: string;
  ida?: string;
  // removed legacy action_id
  properties: {
    action: LocalizedTextMap;
    description?: LocalizedTextMap;
    assigned_to?: KanbanRefId[];
    languages?: string[];
    priority?: number;
    difficulty?: number;
    status?: string;
    percent_complete?: number;
    burndown?: number;
    dates?: Record<string, KanbanDateRecord | null | undefined>;
    remarks?: string;
    linkage?: number;
    sequence?: number;
    kanban_column?: string;
  };
  project_id?: number;
  project_name?: string;
  refs?: Record<string, any>;
  dt_created?: number;
  dt_modified?: number;
  dt_expected?: number | null;
  dt_completed?: number | null;
  dt_start?: number | null;
  dt_deadline?: number | null;
  duration?: number | null;
  created_by?: any;
  updated_by?: any;
  expected_by?: any;
  attachments?: Array<{
    id: number;
    name: string;
    size_bytes: number;
    mime_type: string;
    url?: string;
  }>;
  due_by?: any;
  completed_by?: any;
  start_by?: any;
  end_by?: any;
  project_metadata?: any;
}

export interface LocalizedTextMap {
  [languageCode: string]: string;
}

export interface KanbanRefId {
  id: string;
}

export interface KanbanDateRecord {
  dt: string;
  who: KanbanRefId | null;
}

export interface KanbanTask {
  id: string;
  properties: {
    action: LocalizedTextMap;
    description?: LocalizedTextMap;
    status?: string;
    priority?: number;
    difficulty?: number;
    dates?: Record<string, KanbanDateRecord | null | undefined>;
    assigned_to?: KanbanRefId[];
    linkage?: number;
    remarks?: string;
  };
  project_name?: string;
  assignee?: string;
  assignee_avatar_url?: string;
  dt_start?: string | null;
  dt_expected?: string | null;
  dt_deadline?: string | null;
  dt_completed?: string | null;
  project_metadata?: any;
  created_by?: any;
  updated_by?: any;
  expected_by?: any;
  due_by?: any;
  completed_by?: any;
  start_by?: any;
  end_by?: any;
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
  priority_value?: number;
  difficulty?: number;
  linkage?: number;
  // removed non-WC3 fields
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
