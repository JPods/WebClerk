/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// WC3 ↔ R25 TypeScript alignment interface for SoftDeleteLedger
export interface SoftDeleteLedger {
  contenttype_id: number;
  object_id: number;
  dt_purge: string;
  dt_created: string;
}
