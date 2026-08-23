/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// WC3 ↔ R25 TypeScript alignment interface for Pending
export interface Pending {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  model_name?: string;
  record_id?: string;
  purpose?: string;
  name?: string;
  data?: Record<string, any>;
  dt_processed?: number;
}
