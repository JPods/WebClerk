/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../api/wcapi';

export const fetchReceipts = async (params?: any) => {
  const res = await getRecords('receipt', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchReceiptDetail = async (id: number) => {
  const res = await getRecord('receipt', id);
  return res?.record ?? res;
};

export const createReceipt = async (data: any) => {
  return saveRecord('receipt', data);
};

export const updateReceipt = async (id: number, data: any) => {
  return saveRecord('receipt', { ...data, id });
};

export const deleteReceipt = async (id: number) => {
  return deleteRecord('receipt', id);
};