export interface OrderLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateOrderLineRequest {
  order_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface OrderLineApiTask {
  id: number;
  order_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateOrderLineRequest {
  id: number;
  order_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}