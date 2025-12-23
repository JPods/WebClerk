export interface CustomerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateCustomerRequest {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface CustomerApiTask {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface UpdateCustomerRequest {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}
