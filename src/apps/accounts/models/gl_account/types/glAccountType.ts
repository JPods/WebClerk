/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface GLAccountAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateGLAccountRequest {
  code: string;
  name: string;
  type: string;
  balance?: number;
  category?: string;
  division?: string;
  used_for?: string;
  account_debit?: number;
  account_credit?: number;
  comment?: string;
}

export interface GLAccountApiTask {
  id?: number;
  code: string;
  name: string;
  type: string;
  balance?: number;
  category?: string;
  division?: string;
  used_for?: string;
  account_debit?: number;
  account_credit?: number;
  comment?: string;
}

export interface UpdateGLAccountRequest {
  id: string;
  code: string;
  name: string;
  type: string;
  balance?: number;
  category?: string;
  division?: string;
  used_for?: string;
  account_debit?: number;
  account_credit?: number;
  comment?: string;
}