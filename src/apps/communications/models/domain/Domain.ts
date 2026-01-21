// WC3 ↔ R25 TypeScript alignment interface for Domain
export interface Domain {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  path?: string;
  type?: string;
  comment?: string;
  status?: string;
  sequence?: number;
  count_accessed?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
