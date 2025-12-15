export interface SerialAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateSerialRequest {
  serial_number: string;
  item_id: string;
  status: string;
  description?: string;
}

export interface SerialApiTask {
  id: number;
  uuid: string | null;
  serial_number: string;
  item_id: string;
  status: string;
  description?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateSerialRequest {
  id: number;
  serial_number: string;
  item_id: string;
  status: string;
  description?: string;
}