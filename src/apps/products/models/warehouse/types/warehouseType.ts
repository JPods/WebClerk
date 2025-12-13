export interface WarehouseAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateWarehouseRequest {
  name: string;
  location: string;
  capacity: number;
  manager: string;
}

export interface WarehouseApiTask {
  id: number;
  uuid: string | null;
  name: string;
  location: string;
  capacity: number;
  manager: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateWarehouseRequest {
  id: number;
  name: string;
  location: string;
  capacity: number;
  manager: string;
}