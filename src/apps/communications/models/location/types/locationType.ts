export interface LocationAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateLocationRequest {
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export interface LocationApiTask {
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export interface UpdateLocationRequest {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}