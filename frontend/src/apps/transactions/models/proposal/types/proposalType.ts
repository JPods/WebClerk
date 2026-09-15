/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Proposal Types — matches wc3 TransactionBaseModel
 * @see webClerk3/apps/transactions/models/base_transaction_model.py
 *
 * DB table: proposals (extends TransactionBaseModel)
 */

import { ProposalFormData } from "../utils/proposalSchema";
import type {
  TransactionStatus,
  TransactionParentType,
  TransactionTotals,
  HeaderCost,
  HeaderSell,
  TransactionFinance,
  TransactionRefs,
  TransactionMetadata,
  TransactionPrefs,
  TransactionComments,
  TransactionActions,
} from "@/apps/transactions/types/transactionTypes";

export interface ProposalAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Partial<ProposalFormData> | null;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  /** Show admin/developer JSON envelopes panel */
  isAdmin?: boolean;
}

export interface CreateProposalRequest {
  status?: TransactionStatus;
  priority?: string;
  price_level?: string;
  customer_id?: number;
  vendor_id?: number;
  manufacturer_id?: number;
  parent_id?: number | null;
  parent_model?: TransactionParentType | null;
  total?: number | null;
  balance?: number | null;
  // Denormalized fields from org
  contact_id?: number | null;
  attention?: string | null;
  address_full?: string | null;
  email?: string | null;
  phone?: string | null;
  terms?: string | null;
  terms_id?: number | null;
  conditions_id?: number | null;
  conditions_description?: string | null;
  ida?: string;
  is_active?: boolean;
  totals?: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  flow?: Record<string, unknown>;
  source?: Record<string, unknown>;
  refs?: TransactionRefs;
  metadata?: TransactionMetadata;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
}

export interface ProposalApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  status: TransactionStatus;
  priority?: string;
  price_level?: string;
  customer_id: number;
  vendor_id: number;
  manufacturer_id: number;
  parent_id?: number | null;
  parent_model?: TransactionParentType | null;
  total?: number | null;
  balance?: number | null;
  // Denormalized fields from org
  contact_id?: number | null;
  attention?: string | null;
  address_full?: string | null;
  email?: string | null;
  phone?: string | null;
  terms?: string | null;
  terms_id?: number | null;
  conditions_id?: number | null;
  conditions_description?: string | null;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  totals?: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  flow?: Record<string, unknown>;
  source?: Record<string, unknown>;
  refs?: TransactionRefs;
  metadata?: TransactionMetadata;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
  lines?: unknown[];
}

export interface UpdateProposalRequest extends Partial<CreateProposalRequest> {
  id: number;
  version?: number;
}

/** @deprecated Use ProposalApiTask instead */
export type ProposalApiResponse = ProposalApiTask;

/** @deprecated Use ProposalApiTask instead */
export type Proposal = ProposalApiTask;

export interface ProposalListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: ProposalApiTask[];
}