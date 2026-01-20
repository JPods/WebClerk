import { getRecords, saveRecord, deleteRecord } from '../../../../../wcapi';

export const fetchPurchaseOrderLines = async (params?: any) => {
  const res = await getRecords('tx_purchase_order_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseOrderLine = async (data: any) => {
  return saveRecord('tx_purchase_order_lines', data);
};

export const updatePurchaseOrderLine = async (id: number, data: any) => {
  return saveRecord('tx_purchase_order_lines', { ...data, id });
};

export const deletePurchaseOrderLine = async (id: number) => {
  return deleteRecord('tx_purchase_order_lines', id);
};