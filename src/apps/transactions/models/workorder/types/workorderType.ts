export interface WorkorderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  /** Show admin/developer JSON envelopes panel */
  isAdmin?: boolean;
}

export interface CreateWorkorderRequest {
  workorder_no: string;
}

export interface UpdateWorkorderRequest {
  id: number;
  workorder_no?: string;
}

export interface WorkorderApiTask {
  id: number;
  workorder_no: string;
  dt_created: number;
}