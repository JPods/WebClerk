/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface DomainAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}
export interface CreateDomainRequest {
  path: string;
  type: string;
}
export interface DomainApiTask {
  path: string;
  type: string;
}
export interface UpdateDomainRequest {
  id: string;
  path: string;
  type: string;
}
