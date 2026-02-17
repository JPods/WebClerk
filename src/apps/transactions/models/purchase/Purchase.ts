// Canonical WC3 ↔ R25 Model Alignment
// Purchase Model

export interface WC3Purchase {
  id: string; // readonly
  purchase_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25Purchase {
  id: string;
  purchaseNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - purchase_no (WC3) ↔ purchaseNo (R25)
