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

export interface LocationRefForm {
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
    location: LocationRefForm[];
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
    location: LocationRefForm[];
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
  email: string;
  company?: string;
  name_suffix?: string;
  name_prefix?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
  refs?: RefsApi;
}

export interface UpdateContactRequest extends CreateContactRequest {
  id: string;
  refs: RefsApi;
}
