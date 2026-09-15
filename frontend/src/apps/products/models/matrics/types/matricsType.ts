/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface MatricsAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateMatricsRequest {
  name: string;
  value: number;
  unit: string;
  description?: string;
}

export interface MatricsApiTask {
  id: number;
  uuid: string | null;
  name: string;
  value: number;
  unit: string;
  description?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateMatricsRequest {
  id: number;
  name: string;
  value: number;
  unit: string;
  description?: string;
}