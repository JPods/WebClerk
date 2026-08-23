/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface VariantAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateVariantRequest {
  name: string;
  description: string;
  item_id: string;
  attributes: string; // JSON string of attributes
}

export interface VariantApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  item_id: string;
  attributes: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateVariantRequest {
  id: number;
  name: string;
  description: string;
  item_id: string;
  attributes: string;
}