export interface BillOfMaterialAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateBillOfMaterialRequest {
  name: string;
  description: string;
  product_id: string;
  components: string; // JSON string of components
}

export interface BillOfMaterialApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  product_id: string;
  components: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateBillOfMaterialRequest {
  id: number;
  name: string;
  description: string;
  product_id: string;
  components: string;
}