export interface EmployeeAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmployeeRequest {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface EmployeeApiTask {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface UpdateEmployeeRequest {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}
