/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const createCurrency = async (data: any) => {
  return saveRecord('currency', data);
};

export const updateCurrency = async (data: any) => {
  return saveRecord('currency', data);
};

export const fetchCurrencies = async (params?: any) => {
  const res = await getRecords('currency', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const deleteCurrency = async (id: number) => {
  return deleteRecord('currency', id);
};