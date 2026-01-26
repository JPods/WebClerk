// WC3 ↔ R25 TypeScript alignment interface for AuditLog
export interface AuditLog {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  user_id?: number;
  model_name: string;
  record_id: number;
  action: string;
  changes?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  id_session?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  actions?: Record<string, any>;
  health_rating?: number;
}
