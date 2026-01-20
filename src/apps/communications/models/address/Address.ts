// WC3 ↔ R25 TypeScript alignment interface for Address
export interface Address {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  address1?: string;
  address2?: string;
  address_type?: string;
  city?: string;
  country?: string;
  instructions?: string;
  latitude?: number;
  longitude?: number;
  state?: string;
  zip?: string;
  full?: string;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
