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
  status: "draft" | "sent" | "failed";
  from_email: string;
  to_email: string;
  body: string;
}

export interface EmailApiTask {
  subject: string;
  status: "draft" | "sent" | "failed";
  from_email: string;
  to_email: string;
  body: string;
}

export interface UpdateEmailRequest {
  id: string;
  subject: string;
  status: "draft" | "sent" | "failed";
  from_email: string;
  to_email: string;
  body: string;
}