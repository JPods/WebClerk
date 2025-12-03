export interface PurchaseOrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePurchaseOrderRequest {
  purchase_order_no: string;
}

export interface UpdatePurchaseOrderRequest {
  id: number;
  purchase_order_no?: string;
}

export interface PurchaseOrderApiTask {
  id: number;
  purchase_order_no: string;
  dt_created: number;
}