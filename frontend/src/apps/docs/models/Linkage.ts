/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// TypeScript interface for Linkage model
export interface Linkage {
  id: number;
  purpose?: string;
  name?: string;
  note?: string;
  refs?: {
    links?: Record<string, number[]>;
  };
  // Add other fields as needed for strict alignment
}
