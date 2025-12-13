import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchPurchaseOrders = async (params?: any) => {
  const res = await getRecords('purchaseorder', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseOrder = async (data: any) => {
  return saveRecord('purchaseorder', data);
};

export const updatePurchaseOrder = async (id: number, data: any) => {
  return saveRecord('purchaseorder', { ...data, id });
};

export const deletePurchaseOrder = async (id: number) => {
  return deleteRecord('purchaseorder', id);
};