export interface RepAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateRepRequest {
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  rep_code: string;
}

export interface RepApiTask {
  id: number;
  uuid: string | null;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  rep_code: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateRepRequest {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  rep_code: string;
}