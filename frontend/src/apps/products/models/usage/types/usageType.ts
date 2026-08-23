/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface UsageAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateUsageRequest {
  item_id: string;
  quantity_used: number;
  date_used: string;
  user_id: string;
  notes?: string;
}

export interface UsageApiTask {
  id: number;
  uuid: string | null;
  item_id: string;
  quantity_used: number;
  date_used: string;
  user_id: string;
  notes?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateUsageRequest {
  id: number;
  item_id: string;
  quantity_used: number;
  date_used: string;
  user_id: string;
  notes?: string;
}