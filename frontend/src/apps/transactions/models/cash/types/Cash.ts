/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Cash TypeScript interfaces
 *
 * Based on wc3 Cash model (apps/transactions/models/cash.py)
 * and legacy wc2 Table 28 field layout.
 */

export type CashStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'refunded'
  | 'partially_refunded';

export type CashGateway = 'manual' | 'stripe' | 'paypal' | 'spreedly';

/** Matches wc3 CashMethod model */
export interface CashMethod {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
}

/** Matches wc3 Term model */
export interface Term {
  id: number;
  name: string;
  description?: string;
  days?: number;
  is_active: boolean;
}

/** refs JSONB structure on Cash */
export interface CashRefs {
  order_ids?: number[];
  invoice_ids?: number[];
  customer_id?: number | null;
  contact_id?: number | null;
  source?: { type: string; id: number } | null;
}

/** metadata JSONB structure on Cash */
export interface CashMetadata {
  reconciliation?: Record<string, unknown>;
  gateway_metadata?: Record<string, unknown>;
  processing_fees?: Record<string, unknown>;
  audit_trail?: Array<{ action: string; timestamp: string; user?: string; details?: string }>;
  [key: string]: unknown;
}

/** Core Cash record from wc3 API */
export interface Cash {
  id: number;
  ida?: string;

  // Relations
  invoice_id?: number | null;
  contact_id?: number | null;
  cash_method_id?: number | null;
  term_id?: number | null;

  // Denormalized display fields (from API)
  contact_name?: string;
  customer_name?: string;
  org_id?: number | null;
  invoice_number?: string;
  cash_method_name?: string;

  // Core fields
  amount: number;
  /** Amount still to apply: starts = amount, decremented as applied (Cash.available). */
  available: number;
  dt_cash?: string;
  reference_number?: string;
  notes?: string;

  // Gateway fields
  gateway: CashGateway;
  gateway_transaction_id?: string;
  gateway_payment_intent_id?: string;
  status: CashStatus;
  gateway_response?: Record<string, unknown>;
  dt_processed?: string;
  fee_amount?: number;

  // Reconciliation
  reconciled?: boolean;
  dt_reconciliation?: string;

  // JSONB
  refs?: CashRefs;
  metadata?: CashMetadata;

  // Timestamps
  dt_created?: string;
  dt_modified?: string;
  version?: number;
  is_active?: boolean;
}

/** Shape for creating a new cash */
export interface CreateCashRequest {
  amount: number;
  contact_id: number;
  dt_cash?: string;
  cash_method_id?: number | null;
  term_id?: number | null;
  invoice_id?: number | null;
  reference_number?: string;
  notes?: string;
  status?: CashStatus;
  gateway?: CashGateway;
  refs?: CashRefs;
  metadata?: CashMetadata;
}

/** Shape for updating an existing cash */
export interface UpdateCashRequest extends Partial<CreateCashRequest> {
  id: number;
  version?: number;
}
