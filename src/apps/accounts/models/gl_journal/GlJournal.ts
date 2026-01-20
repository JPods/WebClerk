// WC3 ↔ R25 TypeScript alignment interface for GlJournal
export interface GlJournal {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  account?: string;
  credit?: number;
  debit?: number;
  source?: string;
  type?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
