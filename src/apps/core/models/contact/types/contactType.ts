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
----------------------------- */

export interface CreateContactRequest {
  name_first: string;
  name_last: string;
  name_middle?: string;
  name_suffix?: string;
  name_prefix?: string;
  attention?: string;
  email: string;
  company?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
  customer_id?: number;
  rep_id?: number;
  vendor_id?: number;
  employee_id?: number;
  manufacturer_id?: number;
  project?: string;
  refs?: RefsApi;
}

export interface UpdateContactRequest extends CreateContactRequest {
  id: string;
  refs: RefsApi;
}
