export interface ProposalLineItem {
  item_id?: number;
  ida_item?: string;
  uuid_item?: string;
  description?: string;
  description_text?: string;
  time_lead?: number;
  locations?: any[];
  unit_measure?: string;
  sequence?: number;
  line_number?: number;
  is_deleted?: boolean;
  is_active?: boolean;
  is_archived?: boolean;
}

export interface ProposalLineQuantity {
  placed?: number;
  ordered?: number;
  remaining?: number;
  is_fixed?: boolean;
  precision?: number;
  is_blanket?: boolean;
  increment?: number;
}

export interface ProposalLineCost {
  unit?: number;
  extended?: number;
  shipping?: number;
  handling?: number;
  freight?: number;
  commissions?: number;
  tax_rate?: number;
  tax?: number;
  is_fixed?: boolean;
  precision?: number;
  tax_code?: string;
  tax_code_id?: number;
}

export interface ProposalLinePrice {
  unit?: number;
  discount_percent?: number;
  discount_amount?: number;
  extended?: number;
  is_fixed?: boolean;
  precision?: number;
}

export interface ProposalLineTax {
  sales_rate?: number;
  sales?: number;
  cost_rate?: number;
  cost?: number;
  shipping?: number;
}

export interface ProposalLinePhysical {
  weight?: {
    value?: number;
    unit?: string;
  };
  dimensions?: {
    length?: number;
    width?: number;
    height?: number;
    unit?: string;
  };
  volume?: {
    value?: number;
    unit?: string;
  };
  package_count?: number;
  is_hazmat?: boolean;
}

export interface ProposalLine {
  id: number;
  parent_id: number;
  parent_ref_id: number;
  price_level?: string;
  status?: string;
  item?: ProposalLineItem;
  quantity?: ProposalLineQuantity;
  cost?: ProposalLineCost;
  price?: ProposalLinePrice;
  tax?: ProposalLineTax;
  physical?: ProposalLinePhysical;
  dt_created: string;
  dt_modified: string;
  version: number;
}

export interface CreateProposalLineRequest {
  parent_id: number;
  status?: string;
  item?: ProposalLineItem;
  quantity?: ProposalLineQuantity;
  cost?: ProposalLineCost;
  price?: ProposalLinePrice;
  tax?: ProposalLineTax;
  physical?: ProposalLinePhysical;
}

export interface UpdateProposalLineRequest {
  id: number;
  status?: string;
  item?: ProposalLineItem;
  quantity?: ProposalLineQuantity;
  cost?: ProposalLineCost;
  price?: ProposalLinePrice;
  tax?: ProposalLineTax;
  physical?: ProposalLinePhysical;
}

export interface ProposalLineListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: ProposalLine[];
}