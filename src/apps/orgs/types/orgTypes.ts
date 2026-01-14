/**
 * Organization Types - Matches wc3 OrgBase schema exactly
 * @see webClerk3/apps/orgs/models/base.py
 */

// Org type enum matching Django OrgType.choices
export type OrgType = 'customer' | 'vendor' | 'rep' | 'employee' | 'manufacturer' | 'other';

// Status options
export type OrgStatus = 'active' | 'prospect' | 'inactive' | 'retired' | '';

// Aspect limit constants (match backend ASPECT_LIMITS)
export const ASPECT_LIMITS = {
  contacts: 15,
  locations: 10,
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
  used?: number;
}

export interface OrgBalances {
  open?: number;
  [key: string]: number | undefined;
}

export interface OrgDueBucket {
  range: string;
  amount: number;
}

export interface OrgFinancialMetrics {
  ytd?: { sales?: number };
}

export interface OrgFinancial {
  credit?: OrgCredit;
  balances?: OrgBalances;
  due_buckets?: OrgDueBucket[];
  metrics?: OrgFinancialMetrics;
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
  display_id?: string; // Optional secondary identifier
  company?: string; // alias for display_name
  status: OrgStatus;
  is_active: boolean;
  notes?: string; // Optional notes field
  
  // Aspect JSONB fields
  contacts: OrgContact[];
  locations: OrgLocation[];
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
  
  // Timestamps
  created_at?: string;
  updated_at?: string;
  dt_created?: string;
  dt_modified?: string;
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
  status?: OrgStatus;
  is_active?: boolean;
  contacts?: OrgContact[];
  locations?: OrgLocation[];
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
  locations: [],
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
