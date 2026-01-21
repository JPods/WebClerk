// Canonical WC3 ↔ R25 Model Alignment
// Proposal Model

export interface WC3Proposal {
  id: string; // readonly
  proposal_no: string; // required
  dt_created: string; // readonly, ISO8601
}

export interface R25Proposal {
  id: string;
  proposalNo: string;
  createdAt: string;
}

// Alignment Notes:
// - WC3 uses snake_case, R25 uses camelCase
// - dt_created (WC3) ↔ createdAt (R25)
// - proposal_no (WC3) ↔ proposalNo (R25)
