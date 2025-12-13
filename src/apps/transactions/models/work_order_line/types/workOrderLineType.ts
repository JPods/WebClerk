export interface WorkOrderLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateWorkOrderLineRequest {
  work_order_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface WorkOrderLineApiTask {
  id: number;
  work_order_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateWorkOrderLineRequest {
  id: number;
  work_order_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}