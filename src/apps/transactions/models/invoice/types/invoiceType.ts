export interface InvoiceAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateInvoiceRequest {
  ida: number;
  invoice_no: string;
  status: string;
  company: string;
  attention: string;
  address1: string;
  address2?: string;
  city: string;
  state: string;
  zip: string;
  email?: string;
  phoneCell?: string;
  phone?: string;
  vendor_id?: number;
  manufacturer_id?: number;
  price_level?: string;
  actionBy?: string;
  action?: string;
  actionDate?: string;
  actionTime?: string;
  salesName?: string;
  orderedBy?: string;
  contractDetailTag?: string;
  terms?: string;
  typeSale?: string;
  taxJuris?: string;
  adSource?: string;
  addComment?: string;
  comment?: string;
  contractDetail?: string;
}

export interface UpdateInvoiceRequest {
  id?: number;
  ida: number;
  invoice_no?: string;
  status?: string;
  company?: string;
  attention?: string;
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  email?: string;
  phoneCell?: string;
  phone?: string;
  vendor_id?: number;
  manufacturer_id?: number;
  price_level?: string;
  actionBy?: string;
  action?: string;
  actionDate?: string;
  actionTime?: string;
  salesName?: string;
  orderedBy?: string;
  contractDetailTag?: string;
  terms?: string;
  typeSale?: string;
  taxJuris?: string;
  adSource?: string;
  addComment?: string;
  comment?: string;
  contractDetail?: string;
}

export interface InvoiceApiTask {
  id: number;
  invoice_no: string;
  dt_created: number;
}
