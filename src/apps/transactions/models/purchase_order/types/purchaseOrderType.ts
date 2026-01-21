export interface PurchaseOrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  /** Show admin/developer JSON envelopes panel */
  isAdmin?: boolean;
}

export interface CreatePurchaseOrderRequest {
  purchase_order_no: string;
  receipt_id?: string;
  vendor_pack_list?: string;
  vendor_pack_date?: string;
}

export interface UpdatePurchaseOrderRequest {
  id: number;
  purchase_order_no?: string;
  receipt_id?: string;
  vendor_pack_list?: string;
  vendor_pack_date?: string;
}

export interface PurchaseOrderApiTask {
  id: number;
  purchase_order_no: string;
  dt_created: number;
}