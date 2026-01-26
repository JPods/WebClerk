import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchOrderLines = async (params?: any) => {
  const res = await getRecords('tx_order_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createOrderLine = async (data: any) => {
  return saveRecord('tx_order_lines', data);
};

export const updateOrderLine = async (id: number, data: any) => {
  return saveRecord('tx_order_lines', { ...data, id });
};

export const deleteOrderLine = async (id: number) => {
  return deleteRecord('tx_order_lines', id);
};