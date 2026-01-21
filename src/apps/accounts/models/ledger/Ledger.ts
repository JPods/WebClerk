// WC3 ↔ R25 TypeScript alignment interface for Ledger
export interface Ledger {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  discount_potential?: number;
  dt_discount_due?: string;
  dt_due?: string;
  dt_posted?: string;
  dt_recorded?: string;
  dt_settled?: string;
  is_settled?: boolean;
  is_cleared?: boolean;
  is_void?: boolean;
  source?: string;
  model_name?: string;
  parent_id?: number;
  invoice_id?: number;
  term_id?: number;
  gl_account_id?: number;
  value_available?: number;
  value_original?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
