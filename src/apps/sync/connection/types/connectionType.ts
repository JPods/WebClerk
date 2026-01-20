export interface ConnectionAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateConnectionRequest {
  name: string;
  type: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database?: string;
}

export interface ConnectionApiTask {
  id: number;
  uuid: string | null;
  name: string;
  type: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateConnectionRequest {
  id: number;
  name: string;
  type: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database?: string;
}