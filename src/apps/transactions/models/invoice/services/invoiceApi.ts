import { getRecords, saveRecord, deleteRecord } from '../../../../api/wcapi';

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchInvoices = async (params?: any) => {
  const res = await getRecords('tx_invoices', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createInvoice = async (data: any) => {
  return saveRecord('tx_invoices', data);
};

export const updateInvoice = async (id: number, data: any) => {
  return saveRecord('tx_invoices', { ...data, id });
};

export const deleteInvoice = async (id: number) => {
  return deleteRecord('tx_invoices', id);
};