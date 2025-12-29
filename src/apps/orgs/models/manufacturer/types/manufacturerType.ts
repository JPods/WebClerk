export interface ManufacturerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateManufacturerRequest {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface ManufacturerApiTask {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface UpdateManufacturerRequest {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}
