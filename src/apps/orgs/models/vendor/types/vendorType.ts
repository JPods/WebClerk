export interface VendorAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateVendorRequest {
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  vendor_number: string;
}

export interface VendorApiTask {
  id: number;
  uuid: string | null;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  vendor_number: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateVendorRequest {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  vendor_number: string;
}