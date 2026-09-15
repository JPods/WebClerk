/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface NotificationAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateNotificationRequest {
  user_id: number;
  message: string;
  type: string;
  read: boolean;
}

export interface NotificationApiTask {
  id: number;
  uuid: string | null;
  user_id: number;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
  dt_created: number;
  dt_modified: number;
  version: number;
  is_active: boolean;
}

export interface UpdateNotificationRequest {
  id: number;
  user_id: number;
  message: string;
  type: string;
  read: boolean;
}