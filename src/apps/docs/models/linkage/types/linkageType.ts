export interface LinkageAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateLinkageRequest {
  name: string;
  description?: string;
  source_model: string;
  source_id: number;
  target_model: string;
  target_id: number;
  link_type: string;
}

export interface LinkageApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description?: string;
  source_model: string;
  source_id: number;
  target_model: string;
  target_id: number;
  link_type: string;
  metadata?: unknown;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateLinkageRequest {
  id: number;
  name: string;
  description?: string;
  source_model: string;
  source_id: number;
  target_model: string;
  target_id: number;
  link_type: string;
}