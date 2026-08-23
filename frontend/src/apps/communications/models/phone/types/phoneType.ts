/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// This file defines TypeScript types and interfaces for phone models only.
// Do not place implementation logic here. For logic, use Phone.ts.

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
  name: string;
  country_code: string;
  opt_out: boolean;
  attention: string;
  format: string;
}

export interface PhoneApiTask {
  number: string;
  name: string;
  country_code: string;
  opt_out: boolean;
  attention: string;
  format: string;
}

export interface UpdatePhoneRequest {
  id: string;
  number: string;
  name: string;
  country_code: string;
  opt_out: boolean;
  attention: string;
  format: string;
}
