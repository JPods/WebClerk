/**
 * Transaction Types - Matches wc3 TransactionBaseModel and related schemas
 * @see webClerk3/apps/transactions/models/base_transaction_model.py
 * @see webClerk3/common/models.py (BaseModel mixins)
 */

// --- Status & Choice Types ---
// Matches TRANSACTION_STATUS_CHOICES in apps/transactions/choices.py
// The string union includes Django's canonical values; `| string` allows
// display-layer values like "draft", "pending" used in legacy code.

export type TransactionStatus =
  | ""
  | "planned"
  | "released"
  | "in_progress"
  | "hold"
  | "complete"
  | "canceled"
  | string;

// Matches TRANSACTION_PARENT_MODEL_CHOICES
// Receipt is intentionally excluded: it extends BaseModel (not TransactionBaseModel)
// and uses a separate save flow (flow.py), so it cannot be a parent_model source.
export type TransactionParentType =
  | "proposal"
  | "order"
  | "invoice"
  | "purchase"
  | "workorder"
  | "requisition";

export type ContactPurpose =
  | "billto"
  | "shipto"
  | "attention"
  | "approver"
  | "cc"
  | "notify"
  | "buyer"
  | "seller"
  | string;

// --- Denormalized Link Types ---

export interface ContactDenorm {
  id: number;
  purpose?: ContactPurpose;
  role?: string;
  name_first?: string;
  name_last?: string;
  display_name?: string;
  company?: string;
  title?: string;
  email?: string;
  phone?: string;
  ida_contact?: string;
}

export interface OrgDenorm {
  id: number;
  ida?: string;
  display_name?: string;
  company?: string;         // alias for display_name (set by backend snapshot)
  email?: string;
  phone?: string;
  address_full?: string;
  attention?: string;
  status?: string;
  org_type?: string;
}

export interface ItemDenorm {
  id: number;
  ida_item?: string;
  description?: string;
  sku?: string;
  key_tags?: string[];
}

// --- Refs Structure (from RefsMixin) ---

export interface TransactionRefsLinks {
  contact?: ContactDenorm[];
  customer?: OrgDenorm[];
  vendor?: OrgDenorm[];
  manufacturer?: OrgDenorm[];
  item?: ItemDenorm[];
  email?: Array<{ id: number; email?: string; type?: string }>;
  phone?: Array<{ id: number; number?: string; type?: string }>;
  location?: Array<{
    id: number;
    type?: string;
    address?: Record<string, unknown>;
  }>;
  document?: number[];
  project?: number[];
  warehouse?: number[];
  glaccount?: number[];
  taxjurisdiction?: number[];
  paymentmethod?: number[];
  paymentterm?: number[];
  currency?: number[];
  [key: string]: unknown;
}

export interface TransactionRefs {
  keywords?: string[];
  tags?: string[];
  categories?: string[];
  related_ids?: number[];
  links?: TransactionRefsLinks;
  depends_on?: Record<string, number[]>;
}

// --- Metadata Structure (from MetadataMixin) ---

export interface MetadataHistoryEntry {
  dt?: number;
  contact_id?: number;
}

export interface MetadataHealth {
  rating?: number;
  completeness?: number;
  accuracy?: number;
  freshness?: number;
  consistency?: number;
}

export interface TransactionMetadata {
  security?: string;
  publish?: string;
  priority?: string;
  version?: string;
  access?: {
    view?: number[];
    edit?: number[];
  };
  resources?: {
    required?: Record<string, unknown>;
    allocated?: Record<string, unknown>;
  };
  flow?: Record<string, unknown>;
  source?: Record<string, unknown>;
  history?: {
    created?: MetadataHistoryEntry;
    modified?: MetadataHistoryEntry;
    accessed?: MetadataHistoryEntry;
    verified?: MetadataHistoryEntry;
    synced?: MetadataHistoryEntry;
  };
  health?: MetadataHealth;
  undefined?: Record<string, unknown>;
  flags?: {
    keywords_pending?: boolean;
    schema_rev?: number;
  };
  versioning?: {
    changed_fields?: string[];
    keywords_dt_refreshed?: number;
  };
}

// --- Prefs Structure (from PrefsMixin) ---

export interface TransactionPrefs {
  userdefined?: Record<string, unknown>;
  locale?: string;
  submission?: {
    as_submitted?: {
      data: unknown;
      dt: number;
      by: number;
    };
  };
}

// --- Comments Structure (from CommentsMixin) ---

export interface CommentEntry {
  ts: string;
  by: string | number;
  text: string;
  source?: string;
}

export interface TransactionComments {
  public?: string;
  process?: string;
  partner?: string;
  notes?: CommentEntry[];
  general?: {
    public?: CommentEntry[];
    process?: CommentEntry[];
    foreign?: CommentEntry[];
  };
  records?: Record<
    string,
    {
      public?: CommentEntry[];
      process?: CommentEntry[];
      foreign?: CommentEntry[];
    }
  >;
}

// --- Actions Structure (from ActionsMixin) ---

export interface ActionItem {
  id?: number;
  ida?: string;
  required?: boolean;
  status?: "pending" | "done" | "blocked" | "canceled" | "In progress" | string;
  who?: number;
  who_name?: string;
  when?: number | string;
  what?: string;
  kind?:
    | "followup"
    | "review"
    | "ship"
    | "approve"
    | "call"
    | "email"
    | "task"
    | string;
  priority?: "low" | "normal" | "high" | "urgent" | number;
  difficulty?: number;
  percent_complete?: number;
  progress?: number;
  notes?: string;
  description?: string | Record<string, string>;
  action?: string | Record<string, string>;
  project_name?: string;
  project_id?: number;
  kanban_column?: string;
  assigned_to?: Array<{ id: string | number; name: string }>;
  completed_at?: number | string;
  completed_by?: number;
  extra?: Record<string, unknown>;
}

export interface TransactionActions {
  required?: boolean;
  status?: "pending" | "done" | "blocked";
  who?: number;
  when?: number;
  what?: string;
  kind?: "followup" | "review" | "ship" | "approve" | string;
  extra?: Record<string, unknown>;
  action_next?: {
    who?: string;
    when?: number;
    what?: string;
  };
  items?: ActionItem[];
  ids?: number[];
}

// --- TransactionBaseModel JSONB Fields ---

export interface TransactionTotals {
  subtotal?: number | null;
  discount?: number | null;
  taxable?: number | null;
  tax?: number | null;
  shipping?: number | null;
  other?: number | null;
  total?: number | null;
  cost?: number | null;
  margin?: number | null;
  margin_pc?: number | null;
  received?: number | null;
  balance?: number | null;
}

export interface HeaderCost {
  line_sum_goods?: number | null;
  line_sum_tax?: number | null;
  line_sum_shipping?: number | null;
  line_sum_handling?: number | null;
  handling?: number | null;
  freight?: number | null;
  tax_rate?: number | null;
  tax?: number | null;
  commissions?: number | null;
  total?: number | null;
}

export interface HeaderSell {
  /** Σ line.price.extended — matches WC3 sell.line_sum_goods */
  line_sum_goods?: number | null;
  /** Σ line.price.discount_amount */
  discount?: number | null;
  tax?: number | null;
  shipping?: number | null;
  handling?: number | null;
  other?: number | null;
  /** = line_sum_goods (sell total equals sum of extended prices) */
  total?: number | null;
}

// Aliases used by FinancialsPanel and other UI components
export type TransactionCost = HeaderCost;
export type TransactionSell = HeaderSell;

export interface TransactionFinance {
  sales_tax_id?: number;
  sales_tax_name?: string;
  sales_tax_rate?: number | null;
  sales_tax?: number | null;
  cost_tax_id?: number;
  cost_tax_name?: string;
  cost_tax_rate?: number | null;
  cost_tax?: number | null;
  tax_subtotal?: number | null;
  tax_pc?: number | null;
  collection_expense?: number | null;
  exchange_expense?: number | null;
}

export interface TransactionFlowEntry {
  type: string;
  id: number;
}

export interface TransactionFlow {
  source?: TransactionFlowEntry[];
  children?: TransactionFlowEntry[];
}

export interface TransactionSource {
  campaign_id?: number;
  catalog_id?: number | null;
  vendor_id?: number;
  manufacturer_id?: number;
}

// --- Main Transaction Interface ---

export interface Transaction {
  // Core scalar fields
  id: number;
  uuid?: string;
  ida?: string;

  // Status & priority
  status: TransactionStatus;
  priority?: string;
  price_level?: string;

  // Primary relationship FKs (the source of truth)
  customer_id: number;
  vendor_id: number;
  manufacturer_id: number;
  parent_id?: number | null;
  parent_model?: TransactionParentType | null;

  // Denormalized totals for quick access
  total?: number | null;
  balance?: number | null;

  // JSONB fields from TransactionBaseModel
  totals?: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  flow?: TransactionFlow;
  source?: TransactionSource;
  action?: TransactionActions;

  // JSONB fields from BaseModel mixins
  metadata?: TransactionMetadata;
  refs?: TransactionRefs;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;

  // Lifecycle fields
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  is_locked?: boolean;

  // Timestamps
  dt_created?: string;
  dt_modified?: string;
  created_at?: string;
  updated_at?: string;
  version?: number;
}

// --- Line Item Types ---

export interface LineItem {
  item_id?: number | null;
  ida_item?: string;
  uuid_item?: string;
  description?: string;
  description_text?: string;
  time_lead?: number | null;
  locations?: unknown[];
  unit_measure?: string;
  sequence?: number;
  line_number?: number;
  is_deleted?: boolean;
  is_active?: boolean;
  is_archived?: boolean;
}

export interface LineQuantity {
  staged?: number;
  active?: number;
  remaining?: number;
  is_fixed?: boolean;
  precision?: number;
  is_blanket?: boolean;
  increment?: number;
}

export interface LineCost {
  unit?: number;
  unit_base?: number;
  discount_percent?: number;
  discount_amount?: number;
  extended?: number;
  shipping?: number;
  handling?: number;
  freight?: number;
  commissions?: number;
  tax_rate?: number;
  tax?: number;
  is_fixed?: boolean;
  precision?: number;
  tax_code?: string;
  tax_code_id?: number;
  tax_lookup_id?: number;
}

export interface LinePrice {
  unit?: number;
  unit_base?: number;
  discount_percent?: number;
  discount_amount?: number;
  extended?: number;
  is_fixed?: boolean;
  precision?: number;
}

export interface LineTax {
  sales_rate?: number | null;
  sales?: number | null;
  cost_rate?: number | null;
  cost?: number | null;
  shipping?: number | null;
  tax_service_id?: number;
}

export interface LinePhysical {
  weight?: { value: number; unit: string };
  dimensions?: { length: number; width: number; height: number; unit: string };
  volume?: { value: number; unit: string };
  package_count?: number;
  is_hazmat?: boolean;
}

export interface TransactionLine {
  id: number;
  uuid?: string;
  parent?: number;
  /** Stable, user-visible line sequence number.  Auto-assigned by backend
   *  from parent.line_increment when left at 0.  Used as the primary
   *  identity key in frontend line handlers (replaces id ?? idx fallback). */
  line_number?: number;

  // Line item info
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  price?: LinePrice;
  tax?: LineTax;
  physical?: LinePhysical;

  // From BaseModel
  metadata?: TransactionMetadata;
  refs?: TransactionRefs;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;

  // Timestamps
  dt_created?: string;
  dt_modified?: string;
  version?: number;
}

// --- Field Configuration Types ---

export interface FieldConfig {
  key: string;
  label: string;
  type?:
    | "text"
    | "number"
    | "date"
    | "datetime"
    | "select"
    | "checkbox"
    | "textarea"
    | "json";
  options?: string[];
  mandatory?: boolean;
  locked?: boolean;
  adminOnly?: boolean;
  placeholder?: string;
  helpText?: string;
}

// --- Helper Functions ---

export const getContactDisplayName = (contact: ContactDenorm): string => {
  if (contact.display_name) return contact.display_name;
  const parts = [contact.name_first, contact.name_last].filter(Boolean);
  if (parts.length > 0) return parts.join(" ");
  return `Contact #${contact.id}`;
};

export const formatPurpose = (purpose?: string): string => {
  if (!purpose) return "";
  const mapping: Record<string, string> = {
    billto: "Bill To",
    shipto: "Ship To",
    attention: "Attention",
    approver: "Approver",
    cc: "CC",
    notify: "Notify",
    buyer: "Buyer",
    seller: "Seller",
  };
  return (
    mapping[purpose.toLowerCase()] ||
    purpose.charAt(0).toUpperCase() + purpose.slice(1)
  );
};

export const groupContactsByPurpose = (
  contacts: ContactDenorm[],
): Record<string, ContactDenorm[]> => {
  return contacts.reduce((acc, contact) => {
    const purpose = contact.purpose || "other";
    if (!acc[purpose]) acc[purpose] = [];
    acc[purpose].push(contact);
    return acc;
  }, {} as Record<string, ContactDenorm[]>);
};

// --- Type Guards ---

export const isTransaction = (obj: unknown): obj is Transaction => {
  return (
    typeof obj === "object" && obj !== null && "id" in obj && "status" in obj
  );
};

export const isTransactionLine = (obj: unknown): obj is TransactionLine => {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "id" in obj &&
    ("item" in obj || "quantity" in obj || "price" in obj)
  );
};
