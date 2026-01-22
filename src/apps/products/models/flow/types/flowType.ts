export interface FlowAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateFlowRequest {
  name: string;
  description: string;
  steps: string; // JSON string of steps
}

export interface FlowApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  steps: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateFlowRequest {
  id: number;
  name: string;
  description: string;
  steps: string;
}