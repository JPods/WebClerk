export interface AddressAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateAddressRequest {
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number | string;
  longitude: number | string;
}

export interface AddressApiTask {
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number | string;
  longitude: number | string;
}

export interface UpdateAddressRequest {
  id: string;
  address1: string;
  address2: string;
  address_type: string;
  full: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  latitude: number | string;
  longitude: number | string;
}
