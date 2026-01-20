import { getRecords, saveRecord, deleteRecord } from '../../../../../wcapi';

export const fetchPurchaseReceipts = async (params?: any) => {
  const res = await getRecords('tx_purchase_receipts', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseReceipt = async (data: any) => {
  return saveRecord('tx_purchase_receipts', data);
};

export const updatePurchaseReceipt = async (id: number, data: any) => {
  return saveRecord('tx_purchase_receipts', { ...data, id });
};

export const deletePurchaseReceipt = async (id: number) => {
  return deleteRecord('tx_purchase_receipts', id);
};