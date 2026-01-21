export interface ItemAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateItemRequest {
  name: string;
  description: string;
  price: number;
  category: string;
}

export interface ItemApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  price: number;
  category: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateItemRequest {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
}