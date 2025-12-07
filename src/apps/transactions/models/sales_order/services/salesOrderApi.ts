import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';


export const fetchSalesOrders = async (params?: any) => {
  const res = await getRecords('salesorder', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createSalesOrder = async (data: any) => {
  return saveRecord('salesorder', data);
};

export const updateSalesOrder = async (id: number, data: any) => {
  return saveRecord('salesorder', { ...data, id });
};

export const deleteSalesOrder = async (id: number) => {
  return deleteRecord('salesorder', id);
};