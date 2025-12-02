export interface PhoneAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePhoneRequest {
  number: string;
  type: string;
  country_code: string;
}

export interface PhoneApiTask {
  number: string;
  type: string;
  country_code: string;
}

export interface UpdatePhoneRequest {
  id: string;
  number: string;
  type: string;
  country_code: string;
}