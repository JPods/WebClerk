/**
 * PurchaseLine Types — matches wc3 BaseExecLineModel
 * @see webClerk3/apps/transactions/models/base_line_model.py
 *
 * DB table: purchase_lines (extends BaseExecLineModel)
 * BaseExecLineModel = BaseLineCore (no price JSONB)
 * JSONB fields: item, quantity, cost, tax, physical
 */

import type {
  LineItem,
  LineQuantity,
  LineCost,
  LineTax,
  LinePhysical,
} from "@/apps/transactions/types/transactionTypes";

export interface PurchaseLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePurchaseLineRequest {
  parent_id: number;
  status?: string;
  price_level?: string;
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  tax?: LineTax;
  physical?: LinePhysical;
}

export interface PurchaseLineApiTask {
  id: number;
  parent_id: number;
  parent_ref_id?: number;
  price_level?: string;
  status?: string;
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
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

export interface UpdatePurchaseLineRequest extends Partial<CreatePurchaseLineRequest> {
  id: number;
  version?: number;
}