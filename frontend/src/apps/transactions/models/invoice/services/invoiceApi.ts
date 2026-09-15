/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import {
  getRecords,
  saveRecord,
  deleteRecord,
  getRecord,
} from "@/api/wcapi";
import {
  InvoiceLine,
  CreateInvoiceLineRequest,
  UpdateInvoiceLineRequest,
} from "../../invoice_line/types/invoiceLineType";

export const fetchInvoices = async (params?: any) => {
  const res = await getRecords("invoice", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createInvoice = async (data: any) => {
  return saveRecord("invoice", data);
};

export const updateInvoice = async (id: number, data: any) => {
  return saveRecord("invoice", { ...data, id });
};

export const deleteInvoice = async (id: number) => {
  return deleteRecord("invoice", id);
};

// Invoice Lines API
export const fetchInvoiceLines = async (
  invoiceId: number
): Promise<{
  status: number;
  data: { results: InvoiceLine[]; total: number };
}> => {
  const res = await getRecords("invoice_line", { parent: invoiceId });
  return {
    status: 200,
    data: { results: res.results || [], total: res.total || 0 },
  };
};

export const createInvoiceLine = async (
  invoiceId: number,
  data: CreateInvoiceLineRequest
): Promise<{ status: number; data: InvoiceLine }> => {
  const res = await saveRecord("invoice_line", {
    ...data,
    parent: invoiceId,
  });
  return { status: 200, data: res?.record ?? res };
};

export const updateInvoiceLine = async (
  invoiceId: number,
  lineId: number,
  data: UpdateInvoiceLineRequest
): Promise<{ status: number; data: InvoiceLine }> => {
  const res = await saveRecord("invoice_line", {
    ...data,
    parent: invoiceId,
    id: lineId,
  });
  return { status: 200, data: res?.record ?? res };
};

export const deleteInvoiceLine = async (
  _invoiceId: number,
  lineId: number
): Promise<{ status: number; data: any }> => {
  const res = await deleteRecord("invoice_line", lineId);
  return { status: 200, data: res };
};

export const fetchInvoiceDetail = async (id: number): Promise<any> => {
  const res = await getRecord("invoice", id);
  return res?.record ?? res;
};

export const searchItems = async (
  query: string,
  options?: { limit?: number; extraParams?: Record<string, unknown> }
): Promise<{ status: number; data: { results: any[]; total: number } }> => {
  const trimmed = query?.trim?.() ?? "";
  const params: Record<string, unknown> = {
    limit: options?.limit ?? 25,
    ...(options?.extraParams ?? {}),
  };

  if (trimmed) {
    params.search = trimmed;
    params.key_tags = trimmed;
    params.q = trimmed;
  }

  const res = await getRecords("item", params);
  const results = (res?.results ?? res?.items ?? []) as any[];
  return {
    status: 200,
    data: {
      results,
      total: (res?.total as number | undefined) ?? results.length,
    },
  };
};

export const searchCustomers = async (
  input: { keyword?: string; id?: number; ida?: string; limit?: number } = {}
): Promise<{ status: number; data: { results: any[]; total: number } }> => {
  const { keyword, id, ida, limit = 25 } = input;

  if (Number.isFinite(id) && (id as number) > 0) {
    const detail = await getRecord("customer", id as number);
    const record = detail?.record ?? detail;
    const results = record ? [record] : [];
    return {
      status: 200,
      data: {
        results,
        total: results.length,
      },
    };
  }

  const trimmedKeyword = keyword?.trim?.() ?? "";
  const trimmedIda = ida?.trim?.() ?? "";

  if (!trimmedKeyword && !trimmedIda) {
    return {
      status: 200,
      data: {
        results: [],
        total: 0,
      },
    };
  }

  const params: Record<string, unknown> = { limit };
  if (trimmedKeyword) {
    params.search = trimmedKeyword;
    params.q = trimmedKeyword;
    params.keywords = trimmedKeyword;
    params.display_name = trimmedKeyword;
  }
  if (trimmedIda) {
    params.ida = trimmedIda;
    params.ida_customer = trimmedIda;
    params.customer_code = trimmedIda;
  }

  const res = await getRecords("customer", params);
  const rawResults = (res?.results ?? res?.items ?? []) as any[];

  const filteredResults = trimmedIda
    ? rawResults.filter((record) => {
        const candidates = [
          record?.ida_customer,
          record?.ida,
          record?.customer_code,
          record?.customerId,
          record?.id_customer,
        ];
        return candidates.some((value) => {
          if (typeof value === "string") {
            return value.trim().toLowerCase() === trimmedIda.toLowerCase();
          }
          return false;
        });
      })
    : rawResults;

  return {
    status: 200,
    data: {
      results: filteredResults,
      total: (res?.total as number | undefined) ?? filteredResults.length,
    },
  };
};
