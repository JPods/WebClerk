/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface TagAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateTagRequest {
  name: string;
  slug: string;
  description?: string;
  color?: string;
  category?: string;
}

export interface TagApiTask {
  id: number;
  uuid: string | null;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  category?: string;
  metadata?: unknown;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  parent_id?: number | null;
  sort_order?: number;
}

export interface UpdateTagRequest {
  id: number;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  category?: string;
}