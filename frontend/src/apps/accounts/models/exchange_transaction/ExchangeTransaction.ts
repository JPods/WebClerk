/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// WC3 ↔ R25 TypeScript alignment interface for ExchangeTransaction
export interface ExchangeTransaction {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  name?: string;
  dt_start?: string;
  dt_end?: string;
  exchange?: Record<string, any>;
  currency_base?: string;
  currency_target?: string;
  rate?: number;
  precision_convert?: number;
  precision_display?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
