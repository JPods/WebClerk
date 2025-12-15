export interface OrgItemAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateOrgItemRequest {
  org_id: string;
  item_id: string;
  quantity: number;
  description?: string;
}

export interface OrgItemApiTask {
  id: number;
  uuid: string | null;
  org_id: string;
  item_id: string;
  quantity: number;
  description?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateOrgItemRequest {
  id: number;
  org_id: string;
  item_id: string;
  quantity: number;
  description?: string;
}