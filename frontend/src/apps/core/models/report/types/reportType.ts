/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface ReportAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateReportRequest {
  title: string;
  description?: string;
  type: string;
  parameters?: string;
}

export interface ReportApiTask {
  title: string;
  description?: string;
  type: string;
  parameters?: string;
}

export interface UpdateReportRequest {
  id: string;
  title: string;
  description?: string;
  type: string;
  parameters?: string;
}