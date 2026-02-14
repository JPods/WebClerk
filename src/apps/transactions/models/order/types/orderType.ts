/**
 * Order Types — matches wc3 Order (TransactionBaseModel → BaseModel)
 * @see webClerk3/apps/transactions/models/order.py
 * @see webClerk3/apps/transactions/models/base_transaction_model.py
 *
 * Order adds NO extra columns beyond TransactionBaseModel.
 * DB table: orders
 */

import type {
  TransactionStatus,
  TransactionParentType,
  TransactionTotals,
  HeaderCost,
  HeaderSell,
  TransactionFinance,
  TransactionFlow,
  TransactionSource,
  TransactionRefs,
  TransactionMetadata,
  TransactionPrefs,
  TransactionComments,
  TransactionActions,
} from "@/apps/transactions/types/transactionTypes";

/* ------------------------------------------------------------------ */
/*  Component Props                                                    */
/* ------------------------------------------------------------------ */

export interface OrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  /** Show admin/developer JSON envelopes panel */
  isAdmin?: boolean;
}

/* ------------------------------------------------------------------ */
/*  API Request / Response                                             */
/* ------------------------------------------------------------------ */

/** Fields accepted when creating an order via wcapi saveRecord */
export interface CreateOrderRequest {
  // TransactionBaseModel scalar columns
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
  // CoreModel
  ida?: string;
  is_active?: boolean;
  // TransactionBaseModel JSONB fields
  totals?: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  flow?: TransactionFlow;
  source?: TransactionSource;
  // BaseModel JSONB fields
  refs?: TransactionRefs;
  metadata?: TransactionMetadata;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
}

/** Response shape from saveRecord / getRecord for an order */
export interface OrderApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  // TransactionBaseModel scalar columns
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
  // Timestamps & lifecycle
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  // TransactionBaseModel JSONB fields
  totals?: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  flow?: TransactionFlow;
  source?: TransactionSource;
  // BaseModel JSONB fields
  refs?: TransactionRefs;
  metadata?: TransactionMetadata;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
  // Lines (included when fetching detail via getRecord)
  lines?: unknown[];
}

/** Fields accepted for update (id + version required for concurrency) */
export interface UpdateOrderRequest extends Partial<CreateOrderRequest> {
  id: number;
  version?: number;
}
