export interface SalesOrderLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateSalesOrderLineRequest {
  salesorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface SalesOrderLineApiTask {
  id: number;
  salesorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateSalesOrderLineRequest {
  id: number;
  salesorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}