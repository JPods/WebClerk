// WC3 ↔ R25 TypeScript alignment interface for Document
export interface Document {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  name: string;
  slug?: string;
  status?: string;
  description?: string;
  body?: string;
  comment?: string;
  data?: Record<string, any>;
  confidential?: string;
  copyright?: Record<string, any>;
  count_accessed?: number;
  model_name?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  actions?: Record<string, any>;
  health_rating?: number;
}
