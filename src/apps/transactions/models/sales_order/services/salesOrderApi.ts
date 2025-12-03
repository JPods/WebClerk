import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';


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