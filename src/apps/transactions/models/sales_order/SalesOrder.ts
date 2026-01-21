// Canonical WC3 ↔ R25 Model Alignment
// Sales Order Model

export interface WC3SalesOrder {
  id: string; // readonly
  sales_order_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25SalesOrder {
  id: string;
  salesOrderNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - sales_order_no (WC3) ↔ salesOrderNo (R25)
