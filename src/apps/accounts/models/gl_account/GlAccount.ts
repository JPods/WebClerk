// WC3 ↔ R25 TypeScript alignment interface for GlAccount
export interface GlAccount {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  account_credit?: string;
  account_debit?: string;
  category?: string;
  name?: string;
  type?: string;
  used_for?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
