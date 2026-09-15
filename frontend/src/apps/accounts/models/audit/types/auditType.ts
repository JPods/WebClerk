/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface AuditAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateAuditRequest {
  date: string;
  action: string;
  user: string;
  description: string;
}

export interface AuditApiTask {
  date: string;
  action: string;
  user: string;
  description: string;
}

export interface UpdateAuditRequest {
  id: string;
  date: string;
  action: string;
  user: string;
  description: string;
}