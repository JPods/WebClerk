export interface DomainAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateDomainRequest {
  path: string;
  type: string;
  status?: string;
  metadata?: string;
  comment?: string;
  refs?: string;
  prefs?: string;
}

export interface DomainApiTask {
  path: string;
  type: string;
  status?: string;
  metadata?: string;
  comment?: string;
  refs?: string;
  prefs?: string;
}

export interface UpdateDomainRequest {
  id: string;
  path: string;
  type: string;
  status?: string;
  metadata?: string;
  comment?: string;
  refs?: string;
  prefs?: string;
}