/**
 * Invoice Types — matches wc3 Invoice (TransactionBaseModel → BaseModel)
 * @see webClerk3/apps/transactions/models/invoice.py
 * @see webClerk3/apps/transactions/models/base_transaction_model.py
 *
 * Invoice overrides refs and metadata defaults but adds no extra columns
 * beyond TransactionBaseModel.
 * DB table: invoices
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

export interface InvoiceAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

/* ------------------------------------------------------------------ */
/*  API Request / Response                                             */
/* ------------------------------------------------------------------ */

/** Fields accepted when creating an invoice via wcapi saveRecord */
export interface CreateInvoiceRequest {
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
  // BaseModel JSONB fields (invoice overrides defaults)
  refs?: TransactionRefs | Record<string, unknown>;
  metadata?: TransactionMetadata | Record<string, unknown>;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
}

/** Response shape from saveRecord / getRecord for an invoice */
export interface InvoiceApiTask {
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
  refs?: TransactionRefs | Record<string, unknown>;
  metadata?: TransactionMetadata | Record<string, unknown>;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
  // Lines (included when fetching detail via getRecord)
  lines?: unknown[];
}

/** Fields accepted for update (id + version required for concurrency) */
export interface UpdateInvoiceRequest extends Partial<CreateInvoiceRequest> {
  id: number;
  version?: number;
}
