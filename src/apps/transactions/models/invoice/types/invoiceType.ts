export interface InvoiceAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateInvoiceRequest {
  invoice_no: string;
}

export interface UpdateInvoiceRequest {
  invoice_no?: string;
}

export interface InvoiceApiTask {
  id: number;
  invoice_no: string;
  dt_created: number;
}