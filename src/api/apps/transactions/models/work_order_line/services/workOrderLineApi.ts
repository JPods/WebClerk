import { getRecords, saveRecord, deleteRecord } from '../../../../../wcapi';

export const fetchWorkOrderLines = async (params?: any) => {
  const res = await getRecords('tx_work_order_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createWorkOrderLine = async (data: any) => {
  return saveRecord('tx_work_order_lines', data);
};

export const updateWorkOrderLine = async (id: number, data: any) => {
  return saveRecord('tx_work_order_lines', { ...data, id });
};

export const deleteWorkOrderLine = async (id: number) => {
  return deleteRecord('tx_work_order_lines', id);
};