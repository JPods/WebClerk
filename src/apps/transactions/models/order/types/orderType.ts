export interface OrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  /** Show admin/developer JSON envelopes panel */
  isAdmin?: boolean;
}

export interface CreateOrderRequest {
  order_no: string;
}

export interface UpdateOrderRequest {
  id: number;
  order_no?: string;
}

export interface OrderApiTask {
  id: number;
  order_no: string;
  dt_created: number;
}