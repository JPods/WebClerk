/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const fetchPurchaseLines = async (params?: any) => {
  const res = await getRecords('tx_purchase_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseLine = async (data: any) => {
  return saveRecord('tx_purchase_lines', data);
};

export const updatePurchaseLine = async (id: number, data: any) => {
  return saveRecord('tx_purchase_lines', { ...data, id });
};

export const deletePurchaseLine = async (id: number) => {
  return deleteRecord('tx_purchase_lines', id);
};