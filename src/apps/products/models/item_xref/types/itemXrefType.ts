export interface ItemXrefAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateItemXrefRequest {
  item_id_1: string;
  item_id_2: string;
  relationship_type: string;
  description?: string;
}

export interface ItemXrefApiTask {
  id: number;
  uuid: string | null;
  item_id_1: string;
  item_id_2: string;
  relationship_type: string;
  description?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateItemXrefRequest {
  id: number;
  item_id_1: string;
  item_id_2: string;
  relationship_type: string;
  description?: string;
}