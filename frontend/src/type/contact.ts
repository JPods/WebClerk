/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface CreateContactRequest {
  name_first: string;
  name_last: string;
  name_middle: string;
  email: string;
  phone: string;
  company?: string;
  name_suffix?: string;
  name_prefix?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
}
export interface ContactApiTask {
  name_first: string;
  name_last: string;
  name_middle: string;
  email: string;
  phone: string;
  company?: string;
  name_suffix?: string;
  name_prefix?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
}
