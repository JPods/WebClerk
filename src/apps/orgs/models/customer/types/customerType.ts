export interface CustomerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateCustomerRequest {
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  customer_number: string;
}

export interface CustomerApiTask {
  id: number;
  uuid: string | null;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  customer_number: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateCustomerRequest {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  website?: string;
  customer_number: string;
}