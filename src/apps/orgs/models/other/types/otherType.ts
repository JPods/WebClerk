export interface OtherAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateOtherRequest {
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  other_type: string;
}

export interface OtherApiTask {
  id: number;
  uuid: string | null;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  other_type: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateOtherRequest {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  other_type: string;
}