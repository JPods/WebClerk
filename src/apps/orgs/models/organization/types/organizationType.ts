export interface OrganizationAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateOrganizationRequest {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface OrganizationApiTask {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface UpdateOrganizationRequest {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}
