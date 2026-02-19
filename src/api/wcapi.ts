import apiClient from "./axios";
import { resolveModelName } from "./modelNameResolver";

// Re-export model name utilities for convenience
export {
  resolveModelName,
  urlToModelName,
  modelNameToUrl,
  parseRestfulPath,
  getTransactionType,
} from "./modelNameResolver";

// Basic API envelope type
export interface ApiEnvelope<T = any> {
  status: string;
  error?: any | null;
  code: number;
  message: string;
  data: T;
}

export interface ModelNamesPayload {
  model_names: string[];
  count: number;
}

export interface ModelDetailPayload {
  model: {
    model_name: string;
    fields?: Array<{ name: string; type?: string }>;
    [k: string]: any;
  };
}

export interface GetListPayload {
  model_name: string;
  results: any[];
  total: number;
  limit?: number | null;
  offset?: number;
}

export interface GetDetailPayload {
  model_name: string;
  record: any;
  related?: Record<string, any[]>;
}

export async function getModelNames() {
  try {
    const res = await apiClient.get<ApiEnvelope<ModelNamesPayload>>(
      "/wcapi/model_name/list/",
    );
    return res.data.data;
  } catch (err: any) {
    const status = err?.response?.status;
    if (status === 404) {
      // Fallback: some deployments mount API under /api
      const res2 = await apiClient.get<ApiEnvelope<ModelNamesPayload>>(
        "/api/wcapi/model_name/list/",
      );
      return res2.data.data;
    }
    // Bubble other errors (like 401) so caller can show a helpful message
    throw err;
  }
}

export async function getModelDetail(model_name: string) {
  const resolved = resolveModelName(model_name);
  try {
    const res = await apiClient.get<ApiEnvelope<ModelDetailPayload>>(
      "/wcapi/model_name/detail/",
      { params: { model_name: resolved } },
    );
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<ModelDetailPayload>>(
        "/api/wcapi/model_name/detail/",
        { params: { model_name: resolved } },
      );
      return res2.data.data;
    }
    throw err;
  }
}

export async function getRecords(model_name: string, params?: any) {
  const resolved = resolveModelName(model_name);
  try {
    // Never cache wcapi/get calls - always fetch fresh database records
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(
      `/wcapi/get/`,
      {
        params: { model_name: resolved, ...params },
        cache: false,
      } as any,
    );
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(
        `/api/wcapi/get/`,
        {
          params: { model_name: resolved, ...params },
          cache: false,
        } as any,
      );
      return res2.data.data;
    }
    throw err;
  }
}

export async function getRecord(model_name: string, id: number) {
  const resolved = resolveModelName(model_name);
  try {
    // Disable cache for detail requests to always get fresh data (lines may have changed)
    const res = await apiClient.get<ApiEnvelope<GetDetailPayload>>(
      `/wcapi/get/`,
      {
        params: { model_name: resolved, id },
        cache: false,
      } as any,
    );
    console.log(
      `[wcapi.getRecord] model=${resolved} id=${id} response:`,
      res.data,
    );
    const record = res.data.data?.record;
    if (record && ["order"].includes(resolved)) {
      console.log(`[wcapi.getRecord] lines in response:`, record.lines);
      console.log(`[wcapi.getRecord] lines count:`, record.lines?.length);
      console.log(
        `[wcapi.getRecord] line IDs:`,
        record.lines?.map((l: any) => l.id),
      );
    }
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetDetailPayload>>(
        `/api/wcapi/get/`,
        {
          params: { model_name: resolved, id },
          cache: false,
        } as any,
      );
      return res2.data.data;
    }
    throw err;
  }
}

export async function saveRecord(model_name: string, payload: any) {
  const resolved = resolveModelName(model_name);
  // Extract id and mode from payload if present (they go at root level, not in data)
  const { id, mode, ...data } = payload;
  const body: any = { model_name: resolved, data };
  if (id !== undefined) {
    body.id = id;
  }
  if (mode !== undefined) {
    body.mode = mode;
  }
  console.log("[wcapi.saveRecord] Sending:", {
    model_name,
    resolved,
    payload,
    body,
  });
  try {
    const res = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", body);
    console.log("[wcapi.saveRecord] Response:", res.data);
    return res.data.data;
  } catch (err: any) {
    // Log the full error response so we can diagnose 400/500 errors
    if (err?.response) {
      console.error("[wcapi.saveRecord] Error response:", {
        status: err.response.status,
        data: err.response.data,
        model_name,
        body,
      });
    }
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", body);
      return res2.data.data;
    }
    throw err;
  }
}

/**
 * Save a transaction with lines using the transaction-specific save endpoint.
 * This endpoint handles creating/updating/deleting lines along with the header.
 */
export async function saveTransactionWithLines(
  model_name: string,
  payload: any,
  options?: { verifyCalculations?: boolean; saveOnlyDirty?: boolean },
) {
  const resolved = resolveModelName(model_name);
  // Build the request body in the format expected by WCAPITransactionSaveView
  const body = {
    model_name: resolved,
    record: payload,
    id: payload.id, // record should include lines array
    options: {
      verify_calculations: options?.verifyCalculations ?? false, // Disable verification for now
      save_only_dirty: options?.saveOnlyDirty ?? false, // Save all lines, not just dirty ones
    },
  };

  console.log("[wcapi.saveTransactionWithLines] Saving:", {
    model_name: resolved,
    hasLines: !!payload.lines,
    lineCount: payload.lines?.length,
  });
  console.log(
    "[wcapi.saveTransactionWithLines] Full payload:",
    JSON.stringify(body, null, 2),
  );
  //return false;
  try {
    const res = await apiClient.post<ApiEnvelope<any>>(
      "/wcapi/transaction/save/",
      body,
    );
    console.log("[wcapi.saveTransactionWithLines] Response:", res.data);
    return res.data.data ?? res.data;
  } catch (err: any) {
    console.error(
      "[wcapi.saveTransactionWithLines] Error:",
      err.response?.data || err,
    );
    console.error(
      "[wcapi.saveTransactionWithLines] Error details:",
      err.response?.data?.error?.details || "No details",
    );
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>(
        "/api/wcapi/transaction/save/",
        body,
      );
      return res2.data.data ?? res2.data;
    }
    throw err;
  }
}

export async function deleteRecord(model_name: string, id: number) {
  const resolved = resolveModelName(model_name);
  try {
    const res = await apiClient.get<ApiEnvelope<any>>("/wcapi/delete/", {
      params: { model_name: resolved, id },
    });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<any>>("/api/wcapi/delete/", {
        params: { model_name: resolved, id },
      });
      return res2.data.data;
    }
    throw err;
  }
}

/**
 * Search for items by query string (sku, name, description, etc.)
 */
export async function searchItems(
  query: string,
  options?: { limit?: number },
): Promise<GetListPayload> {
  const params: any = {
    model_name: "item",
    search: query,
  };
  if (options?.limit) {
    params.limit = options.limit;
  }
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(
      "/wcapi/get/",
      { params },
    );
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(
        "/api/wcapi/get/",
        { params },
      );
      return res2.data.data;
    }
    throw err;
  }
}

// Local persistence for field selections per model
const LS_KEY = "adminWorkbench.fieldSelections";
type FieldSelections = Record<string, { list: string[]; detail: string[] }>;

export function loadFieldSelections(): FieldSelections {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveFieldSelections(next: FieldSelections) {
  localStorage.setItem(LS_KEY, JSON.stringify(next));
}

// Settings API for workbench fields
export interface SettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  data: {
    list: string[];
    detail: string[];
  };
}

export async function getWorkbenchFieldsSetting(
  model_name: string,
): Promise<SettingRecord | null> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(
      "/wcapi/get/",
      {
        params: {
          model_name: "setting",
          model_name_filter: model_name,
          purpose: "workbench_fields",
        },
      },
    );
    const results = res.data.data.results || [];
    return results.length > 0 ? results[0] : null;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(
        "/api/wcapi/get/",
        {
          params: {
            model_name: "setting",
            model_name_filter: model_name,
            purpose: "workbench_fields",
          },
        },
      );
      const results = res2.data.data.results || [];
      return results.length > 0 ? results[0] : null;
    }
    throw err;
  }
}

export interface DetailFieldSettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  data: {
    hidden: string[];
    readOnly: string[];
  };
}

export async function getDetailFieldSetting(
  model_name: string,
): Promise<DetailFieldSettingRecord | null> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(
      "/wcapi/get/",
      {
        params: {
          model_name: "setting",
          model_name_filter: model_name,
          purpose: "detail_field_access",
        },
      },
    );
    const results = res.data.data.results || [];
    return results.length > 0 ? (results[0] as DetailFieldSettingRecord) : null;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(
        "/api/wcapi/get/",
        {
          params: {
            model_name: "setting",
            model_name_filter: model_name,
            purpose: "detail_field_access",
          },
        },
      );
      const results = res2.data.data.results || [];
      return results.length > 0
        ? (results[0] as DetailFieldSettingRecord)
        : null;
    }
    throw err;
  }
}

export async function saveDetailFieldSetting(
  setting: DetailFieldSettingRecord,
) {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", {
      ...setting,
      model_name: "setting",
    });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", {
        ...setting,
        model_name: "setting",
      });
      return res2.data.data;
    }
    throw err;
  }
}

export async function getAllWorkbenchFieldsSettings(): Promise<
  SettingRecord[]
> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(
      "/wcapi/get/",
      {
        params: { model_name: "setting", purpose: "workbench_fields" },
      },
    );
    return res.data.data.results || [];
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(
        "/api/wcapi/get/",
        {
          params: { model_name: "setting", purpose: "workbench_fields" },
        },
      );
      return res2.data.data.results || [];
    }
    throw err;
  }
}

export async function saveWorkbenchFieldsSetting(setting: SettingRecord) {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", {
      ...setting,
      model_name: "setting",
    });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>("/wcapi/save/", {
        ...setting,
        model_name: "setting",
      });
      return res2.data.data;
    }
    throw err;
  }
}

/**
 * Log a FK ↔ refs.links mismatch to the backend audit log.
 * Fire-and-forget — errors are logged but never thrown.
 */
export async function logRefsMismatch(payload: {
  parent_model: string;
  parent_id: number;
  related_model: string;
  fk_field: string;
  fk_ids: number[];
  refs_ids: number[];
  caller: string;
}) {
  try {
    await apiClient.post("/wcapi/refs-mismatch/", payload);
  } catch (err) {
    console.warn("[wcapi.logRefsMismatch] Failed to log mismatch:", err);
  }
}
