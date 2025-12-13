export interface ManufacturerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateManufacturerRequest {
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  manufacturer_code: string;
}

export interface ManufacturerApiTask {
  id: number;
  uuid: string | null;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  manufacturer_code: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateManufacturerRequest {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  manufacturer_code: string;
}