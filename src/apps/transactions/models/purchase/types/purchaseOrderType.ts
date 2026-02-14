/**
 * PurchaseOrder Types — matches wc3 TransactionBaseModel
 * @see webClerk3/apps/transactions/models/base_transaction_model.py
 *
 * DB table: purchase_orders (extends TransactionBaseModel)
 */

import type {
  TransactionStatus,
  TransactionParentType,
  TransactionTotals,
  HeaderCost,
  TransactionFinance,
  TransactionRefs,
  TransactionMetadata,
  TransactionPrefs,
  TransactionComments,
  TransactionActions,
} from "@/apps/transactions/types/transactionTypes";

export interface PurchaseOrderAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

export interface CreatePurchaseOrderRequest {
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
  finance?: TransactionFinance;
  flow?: Record<string, unknown>;
  source?: Record<string, unknown>;
  refs?: TransactionRefs;
  metadata?: TransactionMetadata;
  prefs?: TransactionPrefs;
  comments?: TransactionComments;
  actions?: TransactionActions;
}

export interface PurchaseOrderApiTask {
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

export interface UpdatePurchaseOrderRequest extends Partial<CreatePurchaseOrderRequest> {
  id: number;
  version?: number;
}