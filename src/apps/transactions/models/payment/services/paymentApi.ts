/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Payment API service — WCAPI SDK calls for the payment model.
 *
 * Follows the same pattern as orderApi.ts / invoiceApi.ts.
 * Direct REST calls are used only for payment-specific actions
 * not covered by the generic wcapi SDK.
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
import apiClient from '@/api/axios';
import type { Payment, CreatePaymentRequest, UpdatePaymentRequest } from '../types/Payment';

const MODEL = 'payment';

export const fetchPayments = async (params?: Record<string, unknown>) => {
  const res = await getRecords(MODEL, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchPayment = async (id: number): Promise<Payment> => {
  const res = await getRecord(MODEL, id);
  return res?.record ?? res;
};

export const createPayment = async (data: CreatePaymentRequest) =>
  saveRecord(MODEL, data);

export const updatePayment = async (id: number, data: UpdatePaymentRequest) =>
  saveRecord(MODEL, { ...data, id });

export const deletePayment = async (id: number) =>
  deleteRecord(MODEL, id);

/** Payment methods lookup */
export const fetchPaymentMethods = async () => {
  const res = await getRecords('paymentmethod', { is_active: true, limit: 50 });
  return res?.results || [];
};

/** Apply a payment to an invoice via the payment endpoint */
export const applyPaymentToInvoice = async (
  paymentId: number,
  invoiceId: number,
  amount: number,
) => {
  const response = await apiClient.post(
    `/api/transactions/payments/${paymentId}/apply_to_invoice/`,
    { invoice_id: invoiceId, amount },
  );
  return response.data;
};

/** Get payment applications for a payment */
export const fetchPaymentApplications = async (paymentId: number) => {
  const res = await getRecords('paymentapplication', { payment_id: paymentId, limit: 100 });
  return res?.results || [];
};
