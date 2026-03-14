/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../api/wcapi';

const PURCHASE_MODEL_NAME = 'purchase';

export const fetchPurchases = async (params?: any) => {
  const res = await getRecords(PURCHASE_MODEL_NAME, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchase = async (data: any) => {
  return saveRecord(PURCHASE_MODEL_NAME, data);
};

export const updatePurchase = async (id: number, data: any) => {
  return saveRecord(PURCHASE_MODEL_NAME, { ...data, id });
};

export const deletePurchase = async (id: number) => {
  return deleteRecord(PURCHASE_MODEL_NAME, id);
};

export const fetchPurchaseDetail = async (id: number) => {
  const res = await getRecord(PURCHASE_MODEL_NAME, id);
  return res?.record ?? res;
};