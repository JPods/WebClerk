/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface EmailAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmailRequest {
  id: number | string;
  email: string;
  name: string;
  attention?: string;
  type?: string;
  opt_out?: string;
  is_primary: boolean;
  is_verified: boolean;
}

export interface EmailApiTask {
  id: number | string;
  email: string;
  name: string;
  attention: string;
  type?: string;
  opt_out: string;
  is_primary: boolean;
  is_verified: boolean;
}

export interface UpdateEmailRequest {
  id: number | string;
  email: string;
  name: string;
  attention?: string;
  type?: string;
  opt_out?: string;
  is_primary: boolean;
  is_verified: boolean;
}
