export interface RequisitionAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateRequisitionRequest {
  requisition_no: string;
}

export interface UpdateRequisitionRequest {
  id: number;
  requisition_no?: string;
}

export interface RequisitionApiTask {
  id: number;
  requisition_no: string;
  dt_created: number;
}