import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchPurchaseOrders = async (params?: any) => {
  const res = await getRecords('tx_purchase_orders', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseOrder = async (data: any) => {
  return saveRecord('tx_purchase_orders', data);
};

export const updatePurchaseOrder = async (id: number, data: any) => {
  return saveRecord('tx_purchase_orders', { ...data, id });
};

export const deletePurchaseOrder = async (id: number) => {
  return deleteRecord('tx_purchase_orders', id);
};