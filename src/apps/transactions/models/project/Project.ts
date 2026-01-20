// WC3 ↔ R25 TypeScript alignment interface for Project
export interface Project {
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
  situation?: string;
  objective?: Record<string, any>;
  priority?: number;
  status?: string;
  attention?: string;
  id_contact?: number;
  tasks?: Record<string, any>;
  burndown?: number;
  category?: string;
  intent?: string;
  logistics?: Record<string, any>;
  slug?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  actions?: Record<string, any>;
  health_rating?: number;
}
