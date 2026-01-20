export interface PurchaseReceiptAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePurchaseReceiptRequest {
  purchase_order_id: number;
  receipt_date: string;
  received_by: string;
  notes: string;
}

export interface PurchaseReceiptApiTask {
  id: number;
  purchase_order_id: number;
  receipt_date: string;
  received_by: string;
  notes: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdatePurchaseReceiptRequest {
  id: number;
  purchase_order_id: number;
  receipt_date: string;
  received_by: string;
  notes: string;
}