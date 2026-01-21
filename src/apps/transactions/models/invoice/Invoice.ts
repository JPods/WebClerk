// Canonical WC3 ↔ R25 Model Alignment
// Invoice Model

export interface WC3Invoice {
  id: string; // readonly
  invoice_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25Invoice {
  id: string;
  invoiceNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - invoice_no (WC3) ↔ invoiceNo (R25)
