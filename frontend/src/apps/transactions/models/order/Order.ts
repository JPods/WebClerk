/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// Canonical WC3 ↔ R25 Model Alignment
// Order Model (renamed from Sales Order)

export interface WC3Order {
  id: string; // readonly
  order_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25Order {
  id: string;
  orderNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - order_no (WC3) ↔ orderNo (R25)
