/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface Template {
  id: number;
  purpose?: string;
  name?: string;
  data: string;
  dt_processed: number;
  created_at: number;
  updated_at: number;
  is_active: boolean;
}

export interface CreateTemplateRequest {
  purpose?: string;
  name?: string;
  data: string;
}

export interface UpdateTemplateRequest extends CreateTemplateRequest {
  id: number;
}

export interface TemplateApiTask extends Template {}

export interface TemplateAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}