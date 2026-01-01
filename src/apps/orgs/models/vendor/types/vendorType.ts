export interface VendorAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateVendorRequest {
  display_name: string;
  status: string;
  org_type?: string;
  is_active: boolean;
  version?: number;
}

export interface VendorApiTask {
  id: number;
  display_name: string;
  status: string;
  org_type?: string;
  is_active: boolean;
  version?: number;
}

export interface UpdateVendorRequest {
  id: number;
  display_name: string;
  status: string;
  org_type?: string;
  is_active: boolean;
  version?: number;
}
