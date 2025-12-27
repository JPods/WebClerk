export interface LocationAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateLocationRequest {
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number;
  longitude: number;
}

export interface LocationApiTask {
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number;
  longitude: number;
}

export interface UpdateLocationRequest {
  id: string;
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number;
  longitude: number;
}
