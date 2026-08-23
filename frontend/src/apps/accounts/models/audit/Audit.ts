/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// WC3 ↔ R25 TypeScript alignment interface for Audit
export interface Audit {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  purpose?: string;
  name?: string;
  conflicts?: Record<string, any>;
  changes?: Record<string, any>;
  actions?: Record<string, any>;
  recommendations?: Record<string, any>;
  rating?: number;
  is_completed?: boolean;
  priority?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
