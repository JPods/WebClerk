import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';
import { CreateInvoiceRequest, UpdateInvoiceRequest } from '../types/invoiceType';

export const fetchInvoices = async (params?: any) => {
  const res = await getRecords('tx_invoices', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createInvoice = async (data: CreateInvoiceRequest) => {
  return saveRecord('tx_invoices', data);
};

export const updateInvoice = async (id: number, data: UpdateInvoiceRequest) => {
  return saveRecord('tx_invoices', { ...data, id });
};

export const deleteInvoice = async (id: number) => {
  return deleteRecord('tx_invoices', id);
};