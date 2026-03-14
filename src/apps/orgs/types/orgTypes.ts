/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Organization Types - Matches wc3 OrgBase schema exactly
 * @see webClerk3/apps/orgs/models/base.py
 */

// Org type enum matching Django OrgType.choices
export type OrgType = 'customer' | 'vendor' | 'rep' | 'employee' | 'manufacturer' | 'other';

// Status options — matches ORG_STATUS_CHOICES in apps/orgs/choices.py
export type OrgStatus = 'active' | 'prospect' | 'suspended' | 'inactive' | 'retired' | '';

// Aspect limit constants (match backend ASPECT_LIMITS)
export const ASPECT_LIMITS = {
  contacts: 15,
  addresses: 10,
  domains: 10,
  phones: 10,
  emails: 10,
  relations: 50,
  financial: 1,
  docs: 25,
  connections: 1,
  data: 1,
  metrics: 1,
  gl_accounts: 1,
} as const;

// --- Aspect Sub-Types ---

export interface OrgPhone {
  id: number | null;
  type?: string;
  number: string;
  ext?: string;
  primary?: boolean;
}

export interface OrgEmail {
  id: number | null;
  type?: string;
  email: string;
  primary?: boolean;
  bounce_count?: number;
}

export interface OrgContact {
  id: number | null;
  name: string;
  role?: string;
  phones?: OrgPhone[];
  emails?: OrgEmail[];
}

export interface OrgAddress {
  line1?: string;
  line2?: string;
  city?: string;
  state?: string;
  postal?: string;
  country?: string;
}

export interface OrgLocation {
  id: number | null;
  type?: string;
  address: OrgAddress;
  geo?: { lat: number; lng: number };
}

export interface OrgDomain {
  domain: string;
  verified: boolean;
  dt_verified?: number;
}

export interface OrgRelations {
  parents: number[];
  children: number[];
  linked_ids: number[];
}

export interface OrgCredit {
  limit?: number;
  high?: number;
  available?: number;
  used?: number;  // legacy
  terms_days?: number;  // vendor
}

export interface OrgBalances {
  due?: number;
  current?: number;
  open_orders?: number;
  open_pos?: number;  // vendor
  total_exposure?: number;
  open?: number;  // legacy
  [key: string]: number | undefined;
}

export interface OrgAging {
  future?: number;
  period_1?: number;
  period_2?: number;
  period_3?: number;
}

export interface OrgPayment {
  days_avg_paid?: number;
  days_pay?: number;
  dt_last_payment?: string | null;
  last_payment_amount?: number;
}

export interface OrgSales {
  mtd?: number;
  ytd?: number;
  lifetime?: number;
  dt_last_sale?: string | null;
  last_sale_amount?: number;
}

export interface OrgCosts {
  mtd?: number;
  ytd?: number;
}

export interface OrgMargin {
  mtd?: number;
  ytd?: number;
  pct?: number;
}

export interface OrgReturns {
  mtd?: number;
  ytd?: number;
  count?: number;
}

export interface OrgDeposits {
  unapplied?: number;
}

export interface OrgCollection {
  cost_mtd?: number;
  cost_ytd?: number;
  cost_alltime?: number;
}

export interface OrgMinimums {
  order?: number;
  payment?: number;
  purchase?: number;
}

export interface OrgStatCategory {
  issued?: { count: number; value: number };
  canceled?: { count: number; value: number };
  executed?: { count: number; value: number };
}

export interface OrgStats {
  proposals?: OrgStatCategory;
  orders?: OrgStatCategory;
  invoices?: OrgStatCategory;
  payments?: OrgStatCategory;
  purchases?: OrgStatCategory;
}

export interface OrgComplaints {
  our_fault?: number;
  their_fault?: number;
  unresolved?: number;
  costs?: { us?: number; partner?: number; rep?: number };
}

export interface OrgSmallStingCategory {
  count?: number;
  value?: number;
}

export interface OrgSmallStings {
  received?: { count: number; value: number; paid: number; pending: number };
  issued?: { count: number; value: number; collected: number; pending: number };
  by_category?: {
    shipping?: OrgSmallStingCategory;
    billing?: OrgSmallStingCategory;
    quality?: OrgSmallStingCategory;
    service?: OrgSmallStingCategory;
    other?: OrgSmallStingCategory;
  };
}

// --- Type-keyed Financial Sections ---

export interface OrgFinancialCommon {
  currency?: string;
  account?: {
    dt_opened?: string | null;
    dt_last_activity?: string | null;
    hold?: boolean;
    cod_only?: boolean;
    inactive?: boolean;
  };
  rating?: {
    internal?: string | number | null;
    comments?: string;
    credit_score?: number | null;
  };
  settings?: {
    discount_pct?: number;
    tax_exempt?: boolean;
    tax_exempt_id?: string;
    terms_id?: number | null;
    notes?: string;
  };
}

export interface OrgFinancialCustomer {
  credit?: OrgCredit;
  balances?: OrgBalances;
  aging?: OrgAging;
  payment?: OrgPayment;
  sales?: OrgSales;
  margin?: OrgMargin;
  returns?: OrgReturns;
  deposits?: OrgDeposits;
  collection?: OrgCollection;
  minimums?: OrgMinimums;
  stats?: OrgStats;
  complaints?: OrgComplaints;
  small_stings?: OrgSmallStings;
}

export interface OrgFinancialVendor {
  credit?: OrgCredit;
  balances?: OrgBalances;
  aging?: OrgAging;
  purchases?: OrgSales;  // re-using shape
  costs?: OrgCosts;
  payments_made?: { mtd?: number; ytd?: number; dt_last_payment?: string | null };
  minimums?: OrgMinimums;
  stats?: OrgStats;
  complaints?: OrgComplaints;
  small_stings?: OrgSmallStings;
}

export interface OrgFinancialRep {
  commissions?: {
    mtd?: number;
    ytd?: number;
    lifetime?: number;
    pending?: number;
    paid?: number;
    rate_pct?: number;
  };
  sales_credited?: { mtd?: number; ytd?: number; lifetime?: number };
  customers_count?: number;
  stats?: OrgStats;
}

export interface OrgFinancialEmployee {
  payroll?: {
    salary?: number;
    rate_hourly?: number;
    rate_type?: 'salary' | 'hourly' | 'commission';
  };
  expenses?: { mtd?: number; ytd?: number; pending?: number };
  commissions?: { mtd?: number; ytd?: number };
  time?: { hours_mtd?: number; hours_ytd?: number };
}

export interface OrgFinancialManufacturer {
  purchases?: OrgSales;
  rebates?: { earned_ytd?: number; received_ytd?: number; pending?: number };
  pricing_tier?: string | null;
  lead_time_days?: number;
  freight_terms?: string;
  min_order?: number;
  stats?: OrgStats;
}

export interface OrgFx {
  gain_loss_mtd?: number;
  gain_loss_ytd?: number;
  gain_loss_alltime?: number;
}

export interface OrgFinancial {
  common?: OrgFinancialCommon;
  customer?: OrgFinancialCustomer;
  vendor?: OrgFinancialVendor;
  rep?: OrgFinancialRep;
  employee?: OrgFinancialEmployee;
  manufacturer?: OrgFinancialManufacturer;
  fx?: OrgFx;
  // Legacy flat fields for backwards compatibility
  credit?: OrgCredit;
  balances?: OrgBalances;
  due_buckets?: OrgDueBucket[];
  metrics?: OrgFinancialMetrics;
}

export interface OrgDueBucket {
  range: string;
  amount: number;
}

export interface OrgFinancialMetrics {
  ytd?: { sales?: number };
}

export interface OrgDoc {
  id: number | null;
  kind: string;
  name: string;
  size?: number;
  sha256?: string;
}

export interface OrgMetrics {
  counts: Record<string, number>;
  periods: Record<string, Record<string, number>>;
}

// --- Main Organization Interface ---

export interface Organization {
  // Core fields
  id: number;
  uuid?: string;
  org_type: OrgType;
  display_name: string;
  ida?: string; // Alternate identifier (from API)
  display_id?: string; // Optional secondary identifier
  company?: string; // alias for display_name
  contact_id?: number | null; // optional pointer to primary contact
  attention?: string | null; // optional attention line for mailing
  email?: string | null; // optional primary email (denormalized from emails aspect)
  phone?: string | null; // optional primary phone (denormalized from phones aspect)
  price_level?: string | null; // e.g. retail, wholesale
  status: OrgStatus;
  is_active: boolean;
  notes?: string; // Optional notes field
  
  // Aspect JSONB fields
  contacts: OrgContact[];
  addresses: OrgLocation[];
  domains?: OrgDomain[];
  phones: OrgPhone[];
  emails: OrgEmail[];
  relations?: OrgRelations;
  financial?: OrgFinancial;
  docs: OrgDoc[];
  connections?: Record<string, string>;
  data?: Record<string, unknown>;
  metrics?: OrgMetrics;
  gl_accounts?: Record<string, unknown>;
  
  // Common model fields
  refs?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  
  // Lifecycle
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  
  // Mixin fields
  stats?: Record<string, unknown>;
  relationship_stats?: Record<string, unknown>;
  
  // Timestamps (BigIntegerField, millisecond epoch)
  dt_created?: number;
  dt_modified?: number;
  version?: number;
}

// --- API Request/Response Types ---

export interface OrgListParams {
  org_type?: OrgType;
  status?: OrgStatus;
  is_active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
  ordering?: string;
}

export interface OrgListResponse {
  results: Organization[];
  count: number;
  total?: number;
  limit?: number;
  offset?: number;
}

export interface OrgCreateRequest {
  org_type: OrgType;
  display_name: string;
  display_id?: string;
  company?: string;
  contact_id?: number | null;
  attention?: string | null;
  email?: string | null;
  phone?: string | null;
  price_level?: string | null;
  status?: OrgStatus;
  is_active?: boolean;
  notes?: string;
  contacts?: OrgContact[];
  addresses?: OrgLocation[];
  domains?: OrgDomain[];
  phones?: OrgPhone[];
  emails?: OrgEmail[];
  relations?: OrgRelations;
  financial?: OrgFinancial;
  docs?: OrgDoc[];
  connections?: Record<string, string>;
  data?: Record<string, unknown>;
  metrics?: OrgMetrics;
  gl_accounts?: Record<string, unknown>;
}

export interface OrgUpdateRequest extends Partial<OrgCreateRequest> {
  id: number;
  version?: number;
}

// --- Default Values ---

export const DEFAULT_RELATIONS: OrgRelations = {
  parents: [],
  children: [],
  linked_ids: [],
};

export const DEFAULT_FINANCIAL: OrgFinancial = {
  credit: {},
  balances: {},
  due_buckets: [],
  metrics: {},
};

export const DEFAULT_METRICS: OrgMetrics = {
  counts: {},
  periods: {},
};

// --- Helper to create empty org ---

export const createEmptyOrg = (orgType: OrgType): Partial<Organization> => ({
  org_type: orgType,
  display_name: '',
  status: 'active',
  is_active: true,
  contacts: [],
  addresses: [],
  domains: [],
  phones: [],
  emails: [],
  relations: DEFAULT_RELATIONS,
  financial: DEFAULT_FINANCIAL,
  docs: [],
  connections: {},
  data: {},
  metrics: DEFAULT_METRICS,
  gl_accounts: {},
});

// --- Type Guards ---

export const isOrganization = (obj: unknown): obj is Organization => {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'org_type' in obj &&
    'display_name' in obj
  );
};
