import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchSalesOrderLines = async (params?: any) => {
  const res = await getRecords('tx_sales_order_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createSalesOrderLine = async (data: any) => {
  return saveRecord('tx_sales_order_lines', data);
};

export const updateSalesOrderLine = async (id: number, data: any) => {
  return saveRecord('tx_sales_order_lines', { ...data, id });
};

export const deleteSalesOrderLine = async (id: number) => {
  return deleteRecord('tx_sales_order_lines', id);
};