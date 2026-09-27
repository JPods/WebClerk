/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Cash API service — WCAPI SDK calls for the cash model.
 *
 * Follows the same pattern as orderApi.ts / invoiceApi.ts.
 * Direct REST calls are used only for cash-specific actions
 * not covered by the generic wcapi SDK.
 */
import { getRecords, getRecord, saveRecord, deleteRecord, createRecord, refusedFrom } from '@/api/wcapi';
import apiClient from '@/api/axios';
import type { Cash, UpdateCashRequest } from '../types/Cash';

const MODEL = 'cash';

export const fetchCashEntries = async (params?: Record<string, unknown>) => {
  const res = await getRecords(MODEL, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchCash = async (id: number): Promise<Cash> => {
  const res = await getRecord(MODEL, id);
  return res?.record ?? res;
};

export const updateCash = async (id: number, data: UpdateCashRequest) =>
  saveRecord(MODEL, { ...data, id });

export const deleteCash = async (id: number) =>
  deleteRecord(MODEL, id);

/** Fetch public gateway config (environment_key for Spreedly SDK) */
export const fetchGatewayConfig = async () => {
  const res = await apiClient.get('/wcapi/cash/gateway-config/');
  return res.data as {
    environment_key: string;
    test_mode: boolean;
    active_gateway_type: string;
    currency: string;
  };
};

/**
 * Pay an invoice by card (Bill, 2026-09-26, plan §13a): save the Cash fully populated except
 * its money, for its id; then pay. The amount is held in metadata.payservice until the gateway
 * says yes, and only then moves into the Cash's amount and applies to the invoice.
 *   POST /wcapi/cash/              {}  (`new`: the empty Cash, config.is_new)
 *   PUT  /wcapi/cash/<id>/         {purpose: 'connection-payservice', invoice_id, method}
 *   POST /wcapi/cash/<id>/pay/     {amount, payment_method_token}
 * The gateway is called after the Cash is committed; a second pay of the same Cash is
 * refused, so a double-click cannot charge twice. A completed charge applies itself to
 * the invoice. `status` is the Cash's after the charge: completed, failed or processing.
 */
export const processGatewayCash = async (
  invoiceId: number,
  amount: number,
  paymentMethodToken: string,
  method = 'card',
) => {
  // `new` makes the Cash; its fields are the next save (Bill, 2026-09-26). No money yet.
  const saved: any = await createRecord(MODEL, {
    purpose: 'connection-payservice', invoice_id: invoiceId, method,
  });
  const cashId: number = saved?.id ?? saved?.record?.id;
  const res = await apiClient.post(`/wcapi/cash/${cashId}/pay/`, {
    amount,
    payment_method_token: paymentMethodToken,   // secret-guard:allow — a variable; the token exists only at runtime
  });
  const record = res.data?.data?.record ?? {};
  return {
    cash_id: cashId,
    status: record.status as string,
    gateway_transaction_id: (record.gateway_transaction_id ?? '') as string,
    message: (record.gateway_response?.message ?? '') as string,
  };
};

/** Cash methods lookup */
export const fetchCashMethods = async () => {
  const res = await getRecords('cash_method', { is_active: true, limit: 50 });
  return res?.results || [];
};

/**
 * Add cash from a document (release #9, Bill 2026-09-26): POST /wcapi/<model>/<id>/add_cash/.
 * amount is what the document is paid (+) or credited (−). The Cash is saved, then applied on an
 * invoice or receipt; a refused apply keeps the Cash and says why (result.applied.state
 * 'refused'). An order's cash is a deposit. A refusal of the save throws the server's sentence.
 */
export const addCash = async (
  model: 'order' | 'invoice' | 'receipt',
  id: number,
  body: { amount: number | string; method?: string; reference?: string; reason?: string; date?: string },
) => {
  try {
    const res = await apiClient.post(`/wcapi/${model}/${id}/add_cash/`, body);
    return res.data?.data?.result ?? res.data?.data;
  } catch (err) {
    throw new Error(refusedFrom(err, 'Cash not added').message);
  }
};

/** Apply a customer's money to an invoice by rule: none = oldest first; {cash_id, amount} = that payment. */
export const applyBalance = async (invoiceId: number, body: { cash_id?: number; amount?: number | string; reason?: string } = {}) => {
  try {
    const res = await apiClient.post(`/wcapi/invoice/${invoiceId}/apply_balance/`, body);
    return res.data?.data?.result ?? res.data?.data;
  } catch (err) {
    throw new Error(refusedFrom(err, 'Not applied').message);
  }
};
