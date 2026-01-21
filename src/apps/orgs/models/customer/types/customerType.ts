export interface CustomerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onCancel?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export interface CreateCustomerRequest {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface CustomerApiTask {
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface UpdateCustomerRequest {
  id: number;
  display_name: string;
  status: string;
  org_type: string;
  is_active: boolean;
  version: number;
}

export interface CustomerType {
  id: number;
  org_type: "customer";
  contacts?: Array<{id: number; name: string; role?: string; phones?: string[]; emails?: string[]}>;
  locations?: Array<{id: number; type?: string; address?: any; geo?: {lat: number; lng: number}}>; 
  domains?: Array<{domain: string; verified: boolean; dt_verified: number}>;
  phones?: Array<{id: number; type?: string; number?: string; ext?: string; primary?: boolean}>;
  emails?: Array<{id: number; type?: string; email?: string; primary?: boolean; bounce_count?: number}>;
  relations?: {parents: number[]; children: number[]; linked_ids: number[]};
  financial?: {credit?: any; balances?: any; due_buckets?: any[]; metrics?: any};
  docs?: Array<{id: number; kind?: string; name?: string; size?: number; sha256?: string}>;
  connections?: Record<string, string>;
  access?: any;
  data?: any;
  metrics?: {counts?: any; periods?: Record<string, any>};
  gl_accounts?: Record<string, string>;
  // Add other fields as needed for strict alignment
}
