import { getRecords, saveRecord, deleteRecord } from '../../../../api/wcapi';

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchSalesOrders = async (params?: any) => {
  const res = await getRecords('tx_sales_orders', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createSalesOrder = async (data: any) => {
  return saveRecord('tx_sales_orders', data);
};

export const updateSalesOrder = async (id: number, data: any) => {
  return saveRecord('tx_sales_orders', { ...data, id });
};

export const deleteSalesOrder = async (id: number) => {
  return deleteRecord('tx_sales_orders', id);
};