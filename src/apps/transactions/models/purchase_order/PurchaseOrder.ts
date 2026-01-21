// Canonical WC3 ↔ R25 Model Alignment
// Purchase Order Model

export interface WC3PurchaseOrder {
  id: string; // readonly
  purchase_order_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25PurchaseOrder {
  id: string;
  purchaseOrderNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - purchase_order_no (WC3) ↔ purchaseOrderNo (R25)
