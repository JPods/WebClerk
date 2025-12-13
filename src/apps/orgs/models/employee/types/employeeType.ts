export interface EmployeeAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmployeeRequest {
  name: string;
  employee_id: string;
  email: string;
  phone: string;
  hire_date: string;
  department: string;
}

export interface EmployeeApiTask {
  id: number;
  uuid: string | null;
  name: string;
  employee_id: string;
  email: string;
  phone: string;
  hire_date: string;
  department: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateEmployeeRequest {
  id: number;
  name: string;
  employee_id: string;
  email: string;
  phone: string;
  hire_date: string;
  department: string;
}