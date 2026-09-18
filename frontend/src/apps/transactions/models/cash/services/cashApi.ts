/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Cash API service — WCAPI SDK calls for the cash model.
 *
 * Follows the same pattern as orderApi.ts / invoiceApi.ts.
 * Direct REST calls are used only for cash-specific actions
 * not covered by the generic wcapi SDK.
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
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

/** Process a card cash through Spreedly */
export const processGatewayCash = async (
  invoiceId: number,
  amount: number,
  paymentMethodToken: string,
) => {
  const res = await apiClient.post('/wcapi/cash/process/', {
    invoice_id: invoiceId,
    amount,
    payment_method_token: paymentMethodToken,
  });
  return res.data as {
    cash_id: number;
    status: string;
    gateway_transaction_id: string;
    message: string;
  };
};

/** Cash methods lookup */
export const fetchCashMethods = async () => {
  const res = await getRecords('cash_method', { is_active: true, limit: 50 });
  return res?.results || [];
};
