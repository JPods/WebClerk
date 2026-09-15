/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface ProposalLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateProposalLineRequest {
  proposal_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface ProposalLineApiTask {
  id: number;
  proposal_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateProposalLineRequest {
  id: number;
  proposal_id: number;
  item_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
}