/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface CampaignAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateCampaignRequest {
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  status: string;
}

export interface CampaignApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  status: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateCampaignRequest {
  id: number;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  status: string;
}