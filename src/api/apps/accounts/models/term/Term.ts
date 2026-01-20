// WC3 ↔ R25 TypeScript alignment interface for Term
export interface Term {
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
  approved_by?: string;
  day_cut_off_due?: number;
  day_cut_off_invoice?: number;
  days_discount?: number;
  days_due?: number;
  days_in_period?: number;
  description?: string;
  discount_rate?: number;
  period_count?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
