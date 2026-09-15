/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface GLJournalAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateGLJournalRequest {
  date: string;
  description: string;
  amount: number;
  type: string;
}

export interface GLJournalApiTask {
  date: string;
  description: string;
  amount: number;
  type: string;
}

export interface UpdateGLJournalRequest {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: string;
}