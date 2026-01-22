import {
  getRecords,
  saveRecord,
  deleteRecord,
  getRecord,
} from "../../../../../wcapi";
import { patchAction } from "../../../../../userProfile";
import {
  SalesOrderLine,
  CreateSalesOrderLineRequest,
  UpdateSalesOrderLineRequest,
} from "../types/salesOrderLineType";

export const fetchSalesOrders = async (params?: any) => {
  const res = await getRecords("salesorder", params);
  return { status: 200, data: { items: res.results || [] } };
};

// Utility to deduplicate contacts by contact_id+purpose
function dedupeContacts(contacts: any[] = []) {
  const seen = new Set();
  return contacts.filter((c) => {
    const key = `${c.contact_id || c.id}-${c.purpose}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// Utility to strip parent_id from object and lines
function sanitizeSalesOrderPayload(data: any) {
  const clean = { ...data };
  delete clean.parent_id;
  if (clean.lines && Array.isArray(clean.lines)) {
    clean.lines = clean.lines.map((line: any) => {
      const l = { ...line };
      delete l.parent_id;
      return l;
    });
  }
  // Deduplicate contacts if present
  if (clean.refs?.links?.contact && Array.isArray(clean.refs.links.contact)) {
    clean.refs.links.contact = dedupeContacts(clean.refs.links.contact);
  }
  return clean;
}

export const createSalesOrder = async (data: any) => {
  const clean = sanitizeSalesOrderPayload(data);
  return saveRecord("salesorder", clean);
};

export const updateSalesOrder = async (id: number, data: any) => {
  const clean = sanitizeSalesOrderPayload({ ...data, id });
  return saveRecord("salesorder", clean);
};

export const deleteSalesOrder = async (id: number) => {
  return deleteRecord("salesorder", id);
};

// Sales Order Lines API
export const fetchSalesOrderLines = async (
  salesOrderId: number,
): Promise<{
  status: number;
  data: { results: SalesOrderLine[]; total: number };
}> => {
  const res = await getRecords("sales_order_line", { parent: salesOrderId });
  return {
    status: 200,
    data: { results: res.results || [], total: res.total || 0 },
  };
};

export const createSalesOrderLine = async (
  salesOrderId: number,
  data: CreateSalesOrderLineRequest,
): Promise<{ status: number; data: SalesOrderLine }> => {
  const payload = {
    model_name: "sales_order_line",
    ...data,
    parent: salesOrderId,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const updateSalesOrderLine = async (
  salesOrderId: number,
  lineId: number,
  data: UpdateSalesOrderLineRequest,
): Promise<{ status: number; data: SalesOrderLine }> => {
  const payload = {
    model_name: "sales_order_line",
    ...data,
    parent: salesOrderId,
    id: lineId,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const deleteSalesOrderLine = async (
  _salesOrderId: number,
  lineId: number,
): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: "sales_order_line",
    id: lineId,
    method: "delete",
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const fetchSalesOrderDetail = async (id: number): Promise<any> => {
  const res = await getRecord("salesorder", id);
  console.log("[fetchSalesOrderDetail] id:", id);
  console.log("[fetchSalesOrderDetail] res:", res);
  console.log("[fetchSalesOrderDetail] res?.record:", res?.record);
  console.log(
    "[fetchSalesOrderDetail] res?.record?.lines:",
    res?.record?.lines,
  );
  console.log(
    "[fetchSalesOrderDetail] lines count:",
    res?.record?.lines?.length,
  );
  const result = res?.record ?? res;
  console.log("[fetchSalesOrderDetail] returning:", result);
  console.log(
    "[fetchSalesOrderDetail] returning lines count:",
    result?.lines?.length,
  );
  return result;
};

export const searchItems = async (
  query: string,
  options?: { limit?: number; extraParams?: Record<string, unknown> },
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
  input: { keyword?: string; id?: number; ida?: string; limit?: number } = {},
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
