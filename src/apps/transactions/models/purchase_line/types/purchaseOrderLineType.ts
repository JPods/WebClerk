export interface PurchaseOrderLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePurchaseOrderLineRequest {
  purchaseorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface PurchaseOrderLineApiTask {
  id: number;
  purchaseorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdatePurchaseOrderLineRequest {
  id: number;
  purchaseorder_id: number;  // FK matches Django model field name
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}