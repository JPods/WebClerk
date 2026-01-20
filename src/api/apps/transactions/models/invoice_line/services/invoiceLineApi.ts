import { getRecords, deleteRecord, saveRecord } from "../../../../../wcapi";
import type { InvoiceLine } from "../types/invoiceLineType";

export const fetchInvoiceLines = async (): Promise<{
  status: number;
  data: { items: InvoiceLine[]; total: number };
}> => {
  const res = await getRecords("invoice_line", {});
  return {
    status: 200,
    data: { items: res.results || [], total: res.total || 0 },
  };
};

export const fetchInvoiceLine = async (
  id: number
): Promise<{ status: number; data: InvoiceLine }> => {
  const res = await getRecords("invoice_line", { id });
  return {
    status: 200,
    data: res.results?.[0] || null,
  };
};

export const createInvoiceLine = async (
  data: Partial<InvoiceLine>
): Promise<{ status: number; data: InvoiceLine }> => {
  const res = await saveRecord("invoice_line", data);
  return {
    status: 200,
    data: res,
  };
};

export const updateInvoiceLine = async (
  id: number,
  data: Partial<InvoiceLine>
): Promise<{ status: number; data: InvoiceLine }> => {
  const res = await saveRecord("invoice_line", { id, ...data });
  return {
    status: 200,
    data: res,
  };
};

export const deleteInvoiceLine = async (id: number) => {
  return deleteRecord("invoice_line", id);
};
