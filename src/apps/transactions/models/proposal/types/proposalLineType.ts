/**
 * ProposalLine Types — matches wc3 BaseSellLineModel
 * @see webClerk3/apps/transactions/models/base_line_model.py
 *
 * DB table: proposal_lines (extends BaseSellLineModel)
 * BaseSellLineModel = BaseLineCore + price JSONB
 */

import type {
  LineItem,
  LineQuantity,
  LineCost,
  LinePrice,
  LineTax,
  LinePhysical,
} from "@/apps/transactions/types/transactionTypes";

export interface ProposalLine {
  id: number;
  parent_id: number;
  parent_ref_id: number;
  price_level?: string;
  status?: string;
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  price?: LinePrice;
  tax?: LineTax;
  physical?: LinePhysical;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

export interface CreateProposalLineRequest {
  parent_id: number;
  status?: string;
  price_level?: string;
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  price?: LinePrice;
  tax?: LineTax;
  physical?: LinePhysical;
}

export interface UpdateProposalLineRequest extends Partial<CreateProposalLineRequest> {
  id: number;
  version?: number;
}

export interface ProposalLineListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: ProposalLine[];
}

/** @deprecated Use LineItem from transactionTypes */
export type ProposalLineItem = LineItem;
/** @deprecated Use LineQuantity from transactionTypes */
export type ProposalLineQuantity = LineQuantity;
/** @deprecated Use LineCost from transactionTypes */
export type ProposalLineCost = LineCost;
/** @deprecated Use LinePrice from transactionTypes */
export type ProposalLinePrice = LinePrice;
/** @deprecated Use LineTax from transactionTypes */
export type ProposalLineTax = LineTax;
/** @deprecated Use LinePhysical from transactionTypes */
export type ProposalLinePhysical = LinePhysical;