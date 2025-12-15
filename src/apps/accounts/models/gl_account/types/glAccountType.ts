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
  balance: number;
}

export interface GLAccountApiTask {
  code: string;
  name: string;
  type: string;
  balance: number;
}

export interface UpdateGLAccountRequest {
  id: string;
  code: string;
  name: string;
  type: string;
  balance: number;
}