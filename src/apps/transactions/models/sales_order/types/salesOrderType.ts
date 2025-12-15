export interface SalesOrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateSalesOrderRequest {
  sales_order_no: string;
}

export interface UpdateSalesOrderRequest {
  id: number;
  sales_order_no?: string;
}

export interface SalesOrderApiTask {
  id: number;
  sales_order_no: string;
  dt_created: number;
}