/**
 * Contact Types — matches wc3 Contact (StandardLinksMixin + BaseModel + AbstractBaseUser)
 * @see webClerk3/apps/core/models/contact.py
 *
 * DB table: contacts
 * USERNAME_FIELD: email
 * REQUIRED_FIELDS: [name_first, name_last]
 */

/* -----------------------------
   Component Props
----------------------------- */

export interface ContactAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  getContactData?: (contactId?: number) => Promise<void>;
  /** ID passed from WcapiRouteHandler or parent component */
  id?: number;
  /** Alias for id - used by WcapiRouteHandler */
  recordId?: number;
}

/* -----------------------------
   FORM REF TYPES (UI)
----------------------------- */

export interface EmailRefForm {
  id: number;
  name: string;
  address: string;
}

export interface PhoneRefForm {
  id: number;
  name: string;
  number: string;
}

export interface AddressRefForm {
  id: number;
  name: string;
  address: string;
}

export interface RefsForm {
  tags: string[];
  categories: string[];
  keywords: string[];
  related_ids: string[];
  depends_on: Record<string, any>;
  links: {
    rep: string[];
    item: string[];
    email: EmailRefForm[];
    phone: PhoneRefForm[];
    order: string[];
    domain: string[];
    contact: string[];
    customer: string[];
    document: string[];
    address: AddressRefForm[];
    manufacturer: string[];
    project: string[];
    vendor: string[];
  };
}

/* -----------------------------
   API REF TYPES (BACKEND)
----------------------------- */

export interface RefsApi {
  tags: string[];
  categories: string[];
  keywords: string[];
  related_ids: string[];
  depends_on: Record<string, any>;
  links: {
    rep: string[];
    item: string[];
    email: EmailRefForm[];
    phone: PhoneRefForm[];
    order: string[];
    domain: string[];
    contact: string[];
    customer: string[];
    document: string[];
    address: AddressRefForm[];
    manufacturer: string[];
    project: string[];
    vendor: string[];
  };
}

/* -----------------------------
   API REQUESTS
   Matches Django Contact model columns
----------------------------- */

export interface CreateContactRequest {
  // Name fields
  name_first: string;
  name_last: string;
  name_middle?: string;
  name_suffix?: string;
  name_prefix?: string;
  attention?: string;
  // Login / communication
  email: string;
  phone?: string;
  // Org associations (BigIntegerField FKs)
  company?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string; // choices: "" | "user" | "employee" | "admin"
  customer_id?: number;
  rep_id?: number;
  vendor_id?: number;
  employee_id?: number;
  manufacturer_id?: number;
  other_id?: number;
  project?: string;
  // BaseModel JSONB fields
  refs?: RefsApi;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
}

export interface UpdateContactRequest extends CreateContactRequest {
  id: number | string;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
}

/** Full contact record returned by getRecord */
export interface ContactApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  // Name fields
  name_first: string;
  name_last: string;
  name_middle?: string;
  name_suffix?: string;
  name_prefix?: string;
  attention?: string;
  // Login / communication
  email: string;
  // Org associations
  company?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
  customer_id?: number | null;
  rep_id?: number | null;
  vendor_id?: number | null;
  employee_id?: number | null;
  manufacturer_id?: number | null;
  other_id?: number | null;
  // Auth fields (from AbstractBaseUser)
  is_staff?: boolean;
  is_superuser?: boolean;
  dt_joined?: string;
  last_login?: string | null;
  // Timestamps & lifecycle
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  // BaseModel JSONB fields
  refs?: RefsApi;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}
