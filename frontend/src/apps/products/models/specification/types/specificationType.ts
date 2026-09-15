/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface SpecificationAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateSpecificationRequest {
  name: string;
  description: string;
  requirements: string;
  version: string;
}

export interface SpecificationApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  requirements: string;
  version: string;
  dt_created?: number;
  dt_modified?: number;
  is_active?: boolean;
}

export interface UpdateSpecificationRequest {
  id: number;
  name: string;
  description: string;
  requirements: string;
  version: string;
}