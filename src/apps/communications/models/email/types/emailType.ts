export interface EmailAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmailRequest {
  subject: string;
  body: string;
  from_email: string;
  to_email: string;
  status: string;
}

export interface EmailApiTask {
  subject: string;
  body: string;
  from_email: string;
  to_email: string;
  status: string;
}

export interface UpdateEmailRequest {
  id: string;
  subject: string;
  body: string;
  from_email: string;
  to_email: string;
  status: string;
}