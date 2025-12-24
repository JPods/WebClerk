import { ProposalFormData } from "../utils/proposalSchema";

export interface ProposalAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Partial<ProposalFormData> | null;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

// JSON field interfaces
export interface ProposalCost {
  [key: string]: any;
}

export interface ProposalSell {
  [key: string]: any;
}

export interface ProposalFinance {
  [key: string]: any;
}

export interface ProposalFlow {
  [key: string]: any;
}

export interface ProposalSource {
  [key: string]: any;
}

export interface ProposalAction {
  [key: string]: any;
}

// Main Proposal interface
export interface Proposal {
  id: number;
  uuid: string;
  ida?: string;
  status: string;
  priority?: string;
  price_level?: string;
  id_customer: number;
  id_manufacturer?: number;
  id_vendor?: number;
  cost?: ProposalCost;
  sell?: ProposalSell;
  finance?: ProposalFinance;
  flow?: ProposalFlow;
  source?: ProposalSource;
  action?: string | ProposalAction;
  dt_created: string;
  dt_modified: string;
  version: number;
}

// API request interfaces
export interface CreateProposalRequest {
  ida?: string;
  status?: string;
  priority?: string;
  price_level?: string;
  id_customer: number;
  id_manufacturer?: number;
  id_vendor?: number;
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
  actionBy?: string;
  action?: string | ProposalAction;
  actionDate?: string;
  actionTime?: string;
  salesNameId?: string;
  orderedBy?: string;
  contractDetailTag?: string;
  terms?: string;
  typeSale?: string;
  taxJuris?: string;
  adSource?: string;
  addComment?: string;
  comment?: string;
  contractDetail?: string;
  cost?: ProposalCost;
  sell?: ProposalSell;
  finance?: ProposalFinance;
  flow?: ProposalFlow;
  source?: ProposalSource;
}

export interface UpdateProposalRequest {
  id: number;
  ida?: string;
  status?: string;
  priority?: string;
  price_level?: string;
  id_customer?: number;
  id_manufacturer?: number;
  id_vendor?: number;
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
  actionBy?: string;
  action?: string | ProposalAction;
  actionDate?: string;
  actionTime?: string;
  salesNameId?: string;
  orderedBy?: string;
  contractDetailTag?: string;
  terms?: string;
  typeSale?: string;
  taxJuris?: string;
  adSource?: string;
  addComment?: string;
  comment?: string;
  contractDetail?: string;
  cost?: ProposalCost;
  sell?: ProposalSell;
  finance?: ProposalFinance;
  flow?: ProposalFlow;
  source?: ProposalSource;
}

// API response interfaces
export interface ProposalApiResponse {
  id: number;
  uuid: string;
  ida?: string;
  status: string;
  id_customer: number;
  id_vendor?: number;
  cost?: ProposalCost;
  sell?: ProposalSell;
  finance?: ProposalFinance;
  flow?: ProposalFlow;
  source?: ProposalSource;
  action?: string | ProposalAction;
  dt_created: string;
  dt_modified: string;
  version: number;
}

export interface ProposalListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: ProposalApiResponse[];
}