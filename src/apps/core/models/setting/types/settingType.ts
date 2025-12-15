export interface Setting {
  id: number;
  name?: string;
  purpose?: string;
  role?: string;
  model_target?: string;
  data?: any;
  created_at: number;
  updated_at: number;
  is_active: boolean;
}

export interface CreateSettingRequest {
  name?: string;
  purpose?: string;
  role?: string;
  model_target?: string;
  data?: any;
}

export interface UpdateSettingRequest extends CreateSettingRequest {
  id: number;
}

export interface SettingApiTask extends Setting {}

export interface SettingAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}