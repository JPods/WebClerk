/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Payment TypeScript interfaces
 *
 * Based on wc3 Payment model (apps/transactions/models/payment.py)
 * and legacy wc2 Table 28 field layout.
 */

export type PaymentStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'refunded'
  | 'partially_refunded';

export type PaymentGateway = 'manual' | 'stripe' | 'paypal';

/** Matches wc3 PaymentMethod model */
export interface PaymentMethod {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
}

/** Matches wc3 PaymentTerm model */
export interface PaymentTerm {
  id: number;
  name: string;
  description?: string;
  days?: number;
  is_active: boolean;
}

/** refs JSONB structure on Payment */
export interface PaymentRefs {
  order_ids?: number[];
  invoice_ids?: number[];
  customer_id?: number | null;
  contact_id?: number | null;
  source?: { type: string; id: number } | null;
}

/** metadata JSONB structure on Payment */
export interface PaymentMetadata {
  reconciliation?: Record<string, unknown>;
  gateway_metadata?: Record<string, unknown>;
  processing_fees?: Record<string, unknown>;
  audit_trail?: Array<{ action: string; timestamp: string; user?: string; details?: string }>;
  [key: string]: unknown;
}

/** Core Payment record from wc3 API */
export interface Payment {
  id: number;
  ida?: string;

  // Relations
  invoice_id?: number | null;
  contact_id?: number | null;
  paymentmethod_id?: number | null;
  paymentterm_id?: number | null;

  // Denormalized display fields (from API)
  contact_name?: string;
  customer_name?: string;
  org_id?: number | null;
  invoice_number?: string;
  payment_method_name?: string;

  // Core fields
  amount: number;
  dt_payment?: string;
  reference_number?: string;
  notes?: string;

  // Gateway fields
  gateway: PaymentGateway;
  id_gateway_transaction?: string;
  id_gateway_payment_intent?: string;
  status: PaymentStatus;
  gateway_response?: Record<string, unknown>;
  dt_processed?: string;
  fee_amount?: number;

  // Reconciliation
  reconciled?: boolean;
  dt_reconciliation?: string;

  // JSONB
  refs?: PaymentRefs;
  metadata?: PaymentMetadata;

  // Amount tracking (computed or from API)
  amount_available?: number;

  // Timestamps
  dt_created?: string;
  dt_modified?: string;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
}

/** Shape for creating a new payment */
export interface CreatePaymentRequest {
  amount: number;
  contact_id: number;
  dt_payment?: string;
  paymentmethod_id?: number | null;
  paymentterm_id?: number | null;
  invoice_id?: number | null;
  reference_number?: string;
  notes?: string;
  status?: PaymentStatus;
  gateway?: PaymentGateway;
  refs?: PaymentRefs;
  metadata?: PaymentMetadata;
}

/** Shape for updating an existing payment */
export interface UpdatePaymentRequest extends Partial<CreatePaymentRequest> {
  id: number;
  version?: number;
}

/** PaymentApplication — join table linking payments to invoices */
export interface PaymentApplication {
  id: number;
  payment_id: number;
  invoice_id: number;
  amount: number;
  applied_at?: string;
  notes?: string;

  // Denormalized
  payment_amount?: number;
  invoice_number?: string;
}
