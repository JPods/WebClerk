// WC3 ↔ R25 TypeScript alignment interface for TaxJurisdiction
export interface TaxJurisdiction {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  tax_jurisdiction?: string;
  gl_account_payable?: string;
  scripts?: Record<string, any>;
  service_id?: number;
  service_provider?: string;
  tax_name?: string;
  tax_rate_cost?: number;
  tax_rate_on_shipping?: number;
  tax_rate_sales?: number;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
}
