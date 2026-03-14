/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Project Types — matches wc3 Project model
 * @see webClerk3/apps/transactions/models/project.py
 *
 * DB table: projects (extends BaseModel, NOT TransactionBaseModel)
 * Has its own fields: name, objective, tasks, logistics, burndown, etc.
 */

export type ProjectStatus = "" | "planning" | "active" | "on_hold" | "completed" | "canceled" | string;
export type ProjectAttention = "" | "none" | "low" | "medium" | "high" | "critical" | string;

export interface ProjectObjective {
  goal?: string;
  metrics?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ProjectTask {
  backlog?: unknown[];
  counters?: Record<string, number>;
  [key: string]: unknown;
}

export interface ProjectLogistics {
  budget?: number;
  schedule?: Record<string, unknown>;
  resources?: unknown[];
  [key: string]: unknown;
}

export interface ProjectAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateProjectRequest {
  name: string;
  status?: ProjectStatus;
  attention?: ProjectAttention;
  priority?: number;
  situation?: string;
  category?: string;
  intent?: string;
  slug?: string;
  id_contact?: number | null;
  objective?: ProjectObjective;
  tasks?: ProjectTask;
  logistics?: ProjectLogistics;
  burndown?: number;
  profit?: number;
  profit_velocity?: number;
  data?: Record<string, unknown> | null;
  ida?: string;
  is_active?: boolean;
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

export interface ProjectApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  name: string;
  status: ProjectStatus;
  attention?: ProjectAttention;
  priority?: number;
  situation?: string;
  category?: string;
  intent?: string;
  slug?: string;
  id_contact?: number | null;
  dt_kanban?: string | null;
  objective?: ProjectObjective;
  tasks?: ProjectTask;
  logistics?: ProjectLogistics;
  burndown?: number;
  profit?: number;
  profit_velocity?: number;
  data?: Record<string, unknown> | null;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

export interface UpdateProjectRequest extends Partial<CreateProjectRequest> {
  id: number;
  version?: number;
}