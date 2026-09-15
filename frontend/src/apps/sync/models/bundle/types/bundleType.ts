/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface BundleAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateBundleRequest {
  name: string;
  description: string;
  data: string; // JSON string
  version: string;
}

export interface BundleApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  data: string;
  version: string;
  dt_created?: number;
  dt_modified?: number;
  is_active?: boolean;
}

export interface UpdateBundleRequest {
  id: number;
  name: string;
  description: string;
  data: string;
  version: string;
}