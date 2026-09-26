/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Cash API service — WCAPI SDK calls for the cash model.
 *
 * Follows the same pattern as orderApi.ts / invoiceApi.ts.
 * Direct REST calls are used only for cash-specific actions
 * not covered by the generic wcapi SDK.
 */
import { getRecords, getRecord, saveRecord, deleteRecord, wcapiSave } from '@/api/wcapi';
import apiClient from '@/api/axios';
import type { Cash, CreateCashRequest, UpdateCashRequest } from '../types/Cash';

const MODEL = 'cash';

export const fetchCashEntries = async (params?: Record<string, unknown>) => {
  const res = await getRecords(MODEL, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchCash = async (id: number): Promise<Cash> => {
  const res = await getRecord(MODEL, id);
  return res?.record ?? res;
};

export const createCash = async (data: CreateCashRequest) =>
  saveRecord(MODEL, data);

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
 * Pay an invoice by card: save an empty Cash for its id, then charge it (Bill, 2026-09-24).
 *   POST /wcapi/cash/              {invoice_id, amount, method, purpose: 'empty'}
 *   POST /wcapi/cash/<id>/pay/     {payment_method_token}
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
  // The path names the model; the body is the Cash's fields, flat (REST only).
  const saved: any = await wcapiSave<any>(MODEL, {
    invoice_id: invoiceId, amount, method, purpose: 'empty',
  });
  const cashId: number = saved?.id ?? saved?.record?.id;
  const res = await apiClient.post(`/wcapi/cash/${cashId}/pay/`, {
    payment_method_token: paymentMethodToken,
    amount,
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
