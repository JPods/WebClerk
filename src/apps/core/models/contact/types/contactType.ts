export interface ContactAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}
export interface Refs {
  tags: string[];
  categories: string[];
  keywords: string[];
  related_ids: string[];
  depends_on: Record<string, any>;
  links: {
    rep: string[];
    item: string[];
    email: string[];
    order: string[];
    phone: string[];
    domain: string[];
    contact: string[];
    customer: string[];
    document: string[];
    location: string[];
    manufacturer: string[];
    project: string[];
    vendor: string[];
  };
}
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
  refs?: Refs;
}
export interface ContactApiTask {
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
  refs?: Refs;
}
export interface UpdateContactRequest extends CreateContactRequest {
  id: string;
}
