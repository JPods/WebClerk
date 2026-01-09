import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../api/wcapi';
import { InvoiceFormData } from "../utils/invoiceSchema";

const INVOICE_MODEL_NAME = 'invoice';

export const fetchInvoices = async (params?: any) => {
  const res = await getRecords(INVOICE_MODEL_NAME, params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createInvoice = async (data: Partial<InvoiceFormData>) => {
  return saveRecord(INVOICE_MODEL_NAME, data);
};

export const updateInvoice = async (id: number, data: Partial<InvoiceFormData>) => {
  return saveRecord(INVOICE_MODEL_NAME, { ...data, id });
};

export const deleteInvoice = async (id: number) => {
  return deleteRecord(INVOICE_MODEL_NAME, id);
};

export const fetchInvoiceDetail = async (id: number) => {
  const res = await getRecord(INVOICE_MODEL_NAME, id);
  return res?.record ?? res;
};