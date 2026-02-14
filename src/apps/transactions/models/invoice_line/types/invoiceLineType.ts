/**
 * InvoiceLine Types — matches wc3 InvoiceLine (BaseSellLineModel → BaseLineCore → BaseModel)
 * @see webClerk3/apps/transactions/models/invoice_line.py
 * @see webClerk3/apps/transactions/models/base_line_model.py
 *
 * DB table: invoice_lines
 * FK: invoice → transactions.Invoice (related_name="lines", CASCADE, db_column="invoice_id")
 */

import type {
  LineItem,
  LineQuantity,
  LineCost,
  LinePrice,
  LineTax,
  LinePhysical,
} from "@/apps/transactions/types/transactionTypes";

export interface InvoiceLine {
  id?: number;
  uuid?: string;
  ida?: string;
  invoice_id?: number;  // FK to Invoice

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

export interface CreateInvoiceLineRequest {
  invoice_id: number;  // FK to parent Invoice
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

export interface UpdateInvoiceLineRequest extends Partial<CreateInvoiceLineRequest> {
  id: number;
  version?: number;
}
