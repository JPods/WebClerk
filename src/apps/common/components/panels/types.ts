/**
 * Shared Panel Component Types
 * Common interfaces and types for all Panel components
 */

// ---------------------------------------------------------------------------
// User Roles
// ---------------------------------------------------------------------------

/** Available user roles in the system */
export type UserRole =
  | "admin"
  | "superadmin"
  | "super_admin"
  | "administrator"
  | "manager"
  | "user"
  | "viewer"
  | "guest";

/** Admin-level roles that have full access */
export const ADMIN_ROLES: UserRole[] = [
  "admin",
  "superadmin",
  "super_admin",
  "administrator",
];

/** Manager-level roles (includes admin) */
export const MANAGER_ROLES: UserRole[] = [...ADMIN_ROLES, "manager"];

/** Standard user roles (includes manager) */
export const USER_ROLES: UserRole[] = [...MANAGER_ROLES, "user"];

/** All roles including viewers */
export const ALL_ROLES: UserRole[] = [...USER_ROLES, "viewer", "guest"];

// ---------------------------------------------------------------------------
// Entity Types
// ---------------------------------------------------------------------------

/** Entity types that support panels */
export type EntityType =
  // Core
  | "contact"
  | "setting"
  // Orgs
  | "customer"
  | "vendor"
  | "manufacturer"
  | "employee"
  | "rep"
  | "other"
  // Transactions
  | "order"
  | "sales_order"
  | "invoice"
  | "purchase"
  | "purchase_order"
  | "proposal"
  | "workorder"
  | "work_order"
  // Products
  | "item"
  | "category"
  // Communications
  | "email"
  | "phone"
  | "address"
  | "domain"
  // Support
  | "campaign"
  | "project"
  // Sync
  | "bundle"
  | "connection";

// ---------------------------------------------------------------------------
// Permission Types
// ---------------------------------------------------------------------------

/** Panel permission configuration */
export interface PanelPermissions {
  /** Roles that can view this panel (empty = hidden from all) */
  viewRoles: UserRole[];
  /** Roles that can edit data in this panel (empty = read-only for all) */
  editRoles: UserRole[];
}

/** Default permissions for each panel type */
export const DEFAULT_PANEL_PERMISSIONS: Record<string, PanelPermissions> = {
  comments: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  documents: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  qa: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  contactLinks: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  financials: { viewRoles: MANAGER_ROLES, editRoles: ADMIN_ROLES },
  actions: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  shipping: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  communications: { viewRoles: ALL_ROLES, editRoles: USER_ROLES },
  linkages: { viewRoles: ALL_ROLES, editRoles: ADMIN_ROLES },
  metadata: { viewRoles: ADMIN_ROLES, editRoles: ADMIN_ROLES },
  refs: { viewRoles: ADMIN_ROLES, editRoles: ADMIN_ROLES },
  prefs: { viewRoles: USER_ROLES, editRoles: ADMIN_ROLES },
  rawData: { viewRoles: ADMIN_ROLES, editRoles: ADMIN_ROLES },
};

// ---------------------------------------------------------------------------
// Base Panel Props
// ---------------------------------------------------------------------------

/** Base props shared by all Panel components */
export interface BasePanelProps<T = unknown> {
  /** Type of entity (contact, order, customer, etc.) */
  entityType: EntityType;

  /** ID of the entity */
  entityId: number;

  /** The data to display */
  data: T;

  /** Callback when data changes */
  onChange?: (data: T) => void;

  /** Force read-only mode regardless of permissions */
  readOnly?: boolean;

  /** Override default view roles */
  viewRoles?: UserRole[];

  /** Override default edit roles */
  editRoles?: UserRole[];

  /** Additional CSS classes */
  className?: string;

  /** Compact display mode */
  compact?: boolean;

  /** Title override (default: derived from panel type) */
  title?: string;

  /** Whether panel is initially collapsed */
  defaultCollapsed?: boolean;
}

// ---------------------------------------------------------------------------
// JSONB Field Structures
// ---------------------------------------------------------------------------

/** Generic reference link structure */
export interface RefLink {
  id: number;
  ida?: string;
  display?: string;
  name?: string;
  type?: string;
  purpose?: string;
  [key: string]: unknown;
}

/** Entity metadata structure */
export interface EntityMetadata {
  created_at?: string;
  updated_at?: string;
  created_by?: string | number;
  updated_by?: string | number;
  version?: number;
  tags?: string[];
  flags?: Record<string, boolean>;
  display?: Record<string, string>;
  custom?: Record<string, unknown>;
  [key: string]: unknown;
}

/** Entity refs structure for relationships */
export interface EntityRefs {
  links?: {
    contact?: RefLink[];
    customer?: RefLink[];
    vendor?: RefLink[];
    manufacturer?: RefLink[];
    employee?: RefLink[];
    rep?: RefLink[];
    order?: RefLink[];
    invoice?: RefLink[];
    purchase?: RefLink[];
    proposal?: RefLink[];
    workorder?: RefLink[];
    item?: RefLink[];
    email?: RefLink[];
    phone?: RefLink[];
    address?: RefLink[];
    domain?: RefLink[];
    document?: RefLink[];
    project?: RefLink[];
    [key: string]: RefLink[] | undefined;
  };
  lineage?: {
    parent_id?: number;
    parent_type?: string;
    source_id?: number;
    source_type?: string;
  };
  [key: string]: unknown;
}

/** Entity preferences structure */
export interface EntityPrefs {
  display?: {
    layout?: "grid" | "list" | "card" | "table";
    columns?: string[];
    sort?: { field: string; order: "asc" | "desc" };
    theme?: "light" | "dark" | "system";
  };
  notifications?: {
    email?: boolean;
    sms?: boolean;
    push?: boolean;
    frequency?: "immediate" | "daily" | "weekly";
  };
  defaults?: Record<string, unknown>;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Comment Types
// ---------------------------------------------------------------------------

/** Single comment message (aligned with transactions pattern) */
export interface CommentMessage {
  user: string;
  mgs: string;
  time: string;
  user_id?: number | string;
}

/** Legacy comment entry (deprecated - use CommentMessage) */
export interface CommentEntry {
  id?: number | string;
  text: string;
  by?: string;
  ts?: number | string;
  source?: "Public" | "Process" | "Partner" | "Notes";
}

/** Comments structure with tabs */
export interface EntityComments {
  public?: CommentMessage[];
  process?: CommentMessage[];
  partner?: CommentMessage[];
  notes?: CommentMessage[];
}

/** Raw comments from API - may have strings instead of arrays */
export interface RawEntityComments {
  public?: CommentMessage[] | string;
  process?: CommentMessage[] | string;
  partner?: CommentMessage[] | string;
  notes?: CommentMessage[] | string;
}

// ---------------------------------------------------------------------------
// Action Types
// ---------------------------------------------------------------------------

/** Action/task status */
export type ActionStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "on_hold";

/** Action/task priority */
export type ActionPriority = "low" | "normal" | "high" | "urgent";

/** Action/task kind */
export type ActionKind =
  | "task"
  | "followup"
  | "call"
  | "email"
  | "review"
  | "approve"
  | "ship"
  | "other";

/** Single action/task entry */
export interface ActionEntry {
  id?: number | string;
  kind?: ActionKind;
  what?: string;
  who?: string | number;
  when?: number | string;
  status?: ActionStatus;
  priority?: ActionPriority;
  notes?: string;
  created_at?: string;
  completed_at?: string;
}

// ---------------------------------------------------------------------------
// Q&A Types
// ---------------------------------------------------------------------------

/** Single Q&A entry */
export interface QAEntry {
  id?: number | string;
  question: string;
  answer?: string;
  asked_by?: string;
  answered_by?: string;
  asked_at?: string;
  answered_at?: string;
  status?: "open" | "answered" | "closed";
}

// ---------------------------------------------------------------------------
// Document Types
// ---------------------------------------------------------------------------

/** Document/attachment entry */
export interface DocumentEntry {
  id?: number | string;
  name: string;
  url?: string;
  type?: string;
  size?: number;
  uploaded_by?: string;
  uploaded_at?: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// Financial Types
// ---------------------------------------------------------------------------

/** Financial summary structure */
export interface FinancialSummary {
  subtotal?: number;
  total?: number;
  // Tax
  tax_amount?: number;
  tax_percent?: number;
  // Discount
  discount_amount?: number;
  discount_percent?: number;
  // Shipping & Handling
  shipping_amount?: number;
  handling_amount?: number;
  // Margin
  cost?: number;
  margin?: number;
  margin_percent?: number;
  // Payments
  currency?: string;
  payments?: PaymentEntry[];
  balance_due?: number;
}

/** Payment entry for financials */
export interface PaymentEntry {
  id?: number;
  amount?: number;
  method?: string;
  date?: string;
  reference?: string;
}

// ---------------------------------------------------------------------------
// Communication Types (for CommunicationsPanel)
// ---------------------------------------------------------------------------

/** Email link - matches Django LINK_DENORMALIZE_FIELDS.email */
export interface EmailLink extends RefLink {
  email?: string;
  address?: string; // API returns 'address' field
  value?: string; // Normalized 'value' field
  is_primary?: boolean;
  verified?: boolean;
}

/** Phone link - matches Django LINK_DENORMALIZE_FIELDS.phone */
export interface PhoneLink extends RefLink {
  number?: string;
  format?: string;
}

/** Address link - matches Django LINK_DENORMALIZE_FIELDS.location */
export interface AddressLink extends RefLink {
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  full?: string;
}

/** Domain link - matches Django LINK_DENORMALIZE_FIELDS.domain */
export interface DomainLink extends RefLink {
  domain?: string;
  is_primary?: boolean;
  verified?: boolean;
}
