// WC3 ↔ R25 TypeScript alignment interface for Item
export interface Item {
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
  sku?: string;
  kind?: string;
  description?: string;
  price?: Record<string, any>;
  cost?: Record<string, any>;
  category?: string;
  status?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  actions?: Record<string, any>;
  health_rating?: number;
}
