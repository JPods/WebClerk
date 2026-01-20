import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../wcapi';

const PURCHASE_ORDER_MODEL_NAME = 'purchase_order';

export const fetchPurchaseOrders = async (params?: any) => {
  const res = await getRecords(PURCHASE_ORDER_MODEL_NAME, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createPurchaseOrder = async (data: any) => {
  return saveRecord(PURCHASE_ORDER_MODEL_NAME, data);
};

export const updatePurchaseOrder = async (id: number, data: any) => {
  return saveRecord(PURCHASE_ORDER_MODEL_NAME, { ...data, id });
};

export const deletePurchaseOrder = async (id: number) => {
  return deleteRecord(PURCHASE_ORDER_MODEL_NAME, id);
};

export const fetchPurchaseOrderDetail = async (id: number) => {
  const res = await getRecord(PURCHASE_ORDER_MODEL_NAME, id);
  return res?.record ?? res;
};