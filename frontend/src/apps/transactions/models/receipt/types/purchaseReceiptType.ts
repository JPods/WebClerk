/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PurchaseReceipt Types — matches wc3 Receipt model
 * @see webClerk3/apps/transactions/models/receipt.py
 *
 * DB table: receipt (extends BaseModel, NOT TransactionBaseModel)
 * Has its own fields: source_type, dt_received, notes + FKs to purchase/workorder
 */

export type ReceiptSourceType = "purchase_receipt" | "workorder_completion" | "inventory_adjustment" | string;

export interface PurchaseReceiptAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreatePurchaseReceiptRequest {
  source_type?: ReceiptSourceType;
  notes?: string;
  purchase_id?: number | null;
  workorder_id?: number | null;
  ida?: string;
  is_active?: boolean;
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

export interface PurchaseReceiptApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  source_type: ReceiptSourceType;
  dt_received?: string;
  notes?: string;
  purchase_id?: number | null;
  workorder_id?: number | null;
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
  lines?: unknown[];
}

export interface UpdatePurchaseReceiptRequest extends Partial<CreatePurchaseReceiptRequest> {
  id: number;
  version?: number;
}