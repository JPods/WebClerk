export interface ProposalAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateProposalRequest {
  proposal_no: string;
}

export interface UpdateProposalRequest {
  id: number;
  proposal_no?: string;
}

export interface ProposalApiTask {
  id: number;
  proposal_no: string;
  dt_created: number;
}