/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const fetchOrderLines = async (params?: any) => {
  const res = await getRecords('order_line', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createOrderLine = async (data: any) => {
  return saveRecord('order_line', data);
};

export const updateOrderLine = async (id: number, data: any) => {
  return saveRecord('order_line', { ...data, id });
};

export const deleteOrderLine = async (id: number) => {
  return deleteRecord('order_line', id);
};