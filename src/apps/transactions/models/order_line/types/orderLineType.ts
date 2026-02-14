/**
 * OrderLine Types — matches wc3 OrderLine (BaseSellLineModel → BaseLineCore → BaseModel)
 * @see webClerk3/apps/transactions/models/order_line.py
 * @see webClerk3/apps/transactions/models/base_line_model.py
 *
 * DB table: order_lines
 * FK: order → transactions.Order (related_name="lines", CASCADE)
 */

import type {
  LineItem,
  LineQuantity,
  LineCost,
  LinePrice,
  LineTax,
  LinePhysical,
} from "@/apps/transactions/types/transactionTypes";

/* ------------------------------------------------------------------ */
/*  Component Props                                                    */
/* ------------------------------------------------------------------ */

export interface OrderLineAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

/* ------------------------------------------------------------------ */
/*  Main OrderLine type                                                */
/* ------------------------------------------------------------------ */

export interface OrderLineApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  order_id?: number;  // FK to Order

  // BaseLineCore JSONB fields
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  tax?: LineTax;
  physical?: LinePhysical;

  // BaseSellLineModel JSONB field
  price?: LinePrice;

  // BaseLineCore scalar columns
  price_level?: string;
  status?: string;

  // BaseModel JSONB fields
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;

  // Timestamps & lifecycle
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
}

/* ------------------------------------------------------------------ */
/*  API Request / Response                                             */
/* ------------------------------------------------------------------ */

export interface CreateOrderLineRequest {
  order_id: number;  // FK to parent Order
  // BaseLineCore JSONB fields
  item?: LineItem;
  quantity?: LineQuantity;
  cost?: LineCost;
  tax?: LineTax;
  physical?: LinePhysical;
  // BaseSellLineModel JSONB field
  price?: LinePrice;
  // Scalar
  price_level?: string;
  status?: string;
  is_active?: boolean;
}

export interface UpdateOrderLineRequest extends Partial<CreateOrderLineRequest> {
  id: number;
  version?: number;
}