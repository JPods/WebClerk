export interface ProjectAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateProjectRequest {
  name: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
}

export interface ProjectApiTask {
  id: number;
  name: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateProjectRequest {
  id: number;
  name: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
}