export interface ServiceAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateServiceRequest {
  name: string;
  description: string;
  cost: number;
  date: string;
}

export interface ServiceApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  cost: number;
  date: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateServiceRequest {
  id: number;
  name: string;
  description: string;
  cost: number;
  date: string;
}