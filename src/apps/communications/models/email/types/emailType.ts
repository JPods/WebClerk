export interface EmailAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmailRequest {
  email: string;
  name?: string;
  attention?: string;
  type?: string;
}

export interface EmailApiTask {
  email: string;
  name?: string;
  attention?: string;
  type?: string;
}

export interface UpdateEmailRequest {
  id: string;
  email: string;
  name?: string;
  attention?: string;
  type?: string;
}