/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
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

type GetRecordsOptions = {
  cacheExempt?: "default-company";
};

function getBackendErrorMessage(err: any, fallback: string): string {
  const data = err?.response?.data;
  if (!data) {
    return err?.message || fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  const detail = data?.detail;
  const error = data?.error;
  const message = data?.message;

  if (detail === "Insufficient inventory") {
    const sku = data?.sku || data?.item_id || "item";
    const required = data?.required;
    const available = data?.available;
    if (required !== undefined && available !== undefined) {
      return `Transfer failed: insufficient inventory for ${sku} (required ${required}, available ${available})`;
    }
  }

  if (detail === "Transfer quantity exceeds source remaining") {
    const sourceModel = data?.source_model || "source";
    const sourceLineId = data?.source_line_id;
    const requested = data?.requested;
    const remaining = data?.remaining;
    if (
      sourceLineId !== undefined &&
      requested !== undefined &&
      remaining !== undefined
    ) {
      return `Transfer failed: ${sourceModel} line #${sourceLineId} requested ${requested} but only ${remaining} remaining`;
    }
  }

  if (typeof detail === 'object') return JSON.stringify(detail);
  if (typeof error === 'object') return JSON.stringify(error);
  return detail || error || message || err?.message || fallback;
}

/**
 * Wrapper: try /wcapi/ first, fall back to /api/wcapi/ on 404.
 * Some deployments mount the API under /api — this handles both.
 */
async function wcapiGet<T>(path: string, config?: any): Promise<T> {
  try {
    const res = await apiClient.get<ApiEnvelope<T>>(`/wcapi/${path}`, config);
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<T>>(`/api/wcapi/${path}`, config);
      return res2.data.data;
    }
    throw err;
  }
}

async function wcapiPost<T>(path: string, body: any): Promise<T> {
  try {
    const res = await apiClient.post<ApiEnvelope<T>>(`/wcapi/${path}`, body);
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<T>>(`/api/wcapi/${path}`, body);
      return res2.data.data;
    }
    throw err;
  }
}

export async function getModelNames() {
  return wcapiGet<ModelNamesPayload>("model_name/list/");
}

export async function getModelDetail(model_name: string) {
  const resolved = resolveModelName(model_name);
  return wcapiGet<ModelDetailPayload>("model_name/detail/", {
    params: { model_name: resolved },
  });
}

export async function getRecords(
  model_name: string,
  params?: any,
  options?: GetRecordsOptions,
) {
  const resolved = resolveModelName(model_name);
  const normalizedParams = { ...(params || {}) };

  // Standardize list search param to `keyword` for wcapi/get parity with wc3.
  if (normalizedParams.keyword == null) {
    if (
      typeof normalizedParams.search === "string" &&
      normalizedParams.search.trim()
    ) {
      normalizedParams.keyword = normalizedParams.search;
    } else if (
      typeof normalizedParams.q === "string" &&
      normalizedParams.q.trim()
    ) {
      normalizedParams.keyword = normalizedParams.q;
    }
  }

  delete normalizedParams.search;
  delete normalizedParams.q;

  const allowDefaultCompanyCache = options?.cacheExempt === "default-company";
  const headers = allowDefaultCompanyCache
    ? { "x-wcapi-cache-exempt": "default-company" }
    : undefined;
  return wcapiGet<GetListPayload>("get/", {
    params: { model_name: resolved, ...normalizedParams },
    cache: allowDefaultCompanyCache,
    headers,
  } as any);
}

// ---------------------------------------------------------------------------
// Cached option getters for dropdowns (contact, project)
// These are expensive to fetch and rarely change within a session
// ---------------------------------------------------------------------------

export interface OptionRecord {
  id: string;
  label?: string;
  name?: string;
  intent?: string;
}

type OptionCacheEntry = {
  data: OptionRecord[];
  timestamp: number;
};

const optionCache = new Map<string, OptionCacheEntry>();
const optionInFlight = new Map<string, Promise<OptionRecord[]>>();
const OPTION_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function getCachedOptions(
  modelName: string,
  params: Record<string, any>,
  mapFn: (record: any) => OptionRecord,
): Promise<OptionRecord[]> {
  const cacheKey = `${modelName}:${JSON.stringify(params)}`;

  // Check cache validity
  const cached = optionCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < OPTION_CACHE_TTL) {
    return cached.data;
  }

  // Return in-flight promise if exists
  if (optionInFlight.has(cacheKey)) {
    return optionInFlight.get(cacheKey)!;
  }

  // Fetch fresh data
  const fetchPromise = (async () => {
    try {
      const response: any = await getRecords(modelName, params);
      const records: any[] =
        response?.results || response?.data || response?.items || [];
      const options = records
        .filter((r: any) => r.id != null)
        .map(mapFn)
        .sort((a, b) =>
          (a.label || a.name || "").localeCompare(b.label || b.name || ""),
        );
      optionCache.set(cacheKey, { data: options, timestamp: Date.now() });
      return options;
    } finally {
      optionInFlight.delete(cacheKey);
    }
  })();

  optionInFlight.set(cacheKey, fetchPromise);
  return fetchPromise;
}

export async function getContactOptions(): Promise<OptionRecord[]> {
  return getCachedOptions(
    "contact",
    { is_active: true, limit: 500 },
    (r: any) => ({
      id: String(r.id),
      label: r.attention || r.name || `Contact #${r.id}`,
    }),
  );
}

export async function getProjectOptions(): Promise<OptionRecord[]> {
  return getCachedOptions(
    "project",
    { is_active: true, limit: 500 },
    (r: any) => ({
      id: String(r.id),
      name: r.name || undefined,
      intent: r.intent || undefined,
    }),
  );
}

/** Clear cache for specific model or all options */
export function clearOptionCache(modelName?: string): void {
  if (modelName) {
    for (const key of optionCache.keys()) {
      if (key.startsWith(`${modelName}:`)) {
        optionCache.delete(key);
      }
    }
  } else {
    optionCache.clear();
  }
}

export async function getRecord(model_name: string, id: number) {
  const resolved = resolveModelName(model_name);
  return wcapiGet<GetDetailPayload>("get/", {
    params: { model_name: resolved, id },
    cache: false,
  } as any);
}

export async function saveRecord(model_name: string, payload: any) {
  const resolved = resolveModelName(model_name);
  // Extract id and mode from payload if present (they go at root level, not in data)
  const { id, mode, ...record } = payload;
  // Always use `record` wrapper — `data` wrapper is deprecated (fixed 2026-06).
  const body: any = { model_name: resolved, record };
  if (id !== undefined) {
    body.id = id;
  }
  if (mode !== undefined) {
    body.mode = mode;
  }
  try {
    return await wcapiPost<any>("save/", body);
  } catch (err: any) {
    throw new Error(getBackendErrorMessage(err, "Save failed"));
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
  // Strip read-only and calculated fields — only send what the server needs
  const {
    uuid: _u, customer_config: _cc, customer_company: _cco,
    totals: _t, actions: _a, refs: _r, metadata: _m,
    sell: _s, cost: _co, finance: _f, flow: _fl,
    prefs: _p, commission: _cm, health_rating: _hr,
    dt_created: _dc, dt_modified: _dm,
    is_archived: _ia, is_deleted: _id2, is_locked: _il,
    security_level: _sl, version: _v,
    ...cleanPayload
  } = payload;
  // Strip read-only/calculated fields from lines too
  if (cleanPayload.lines) {
    cleanPayload.lines = cleanPayload.lines.map((line: any) => {
      const { uuid: _lu, metadata: _lm, prefs: _lp,
        physical: _lph, actions: _la, tax: _lt,
        dt_created: _ldc, dt_modified: _ldm, health_rating: _lhr,
        is_archived: _lia, is_deleted: _lid, is_locked: _lil,
        security_level: _lsl, version: _lv,
        ...cleanLine } = line;
      return cleanLine;
    });
  }
  // Build the request body in the format expected by WCAPITransactionSaveView
  const body = {
    model_name: resolved,
    record: cleanPayload,
    id: cleanPayload.id, // record should include lines array
    options: {
      verify_calculations: options?.verifyCalculations ?? false, // Disable verification for now
      save_only_dirty: options?.saveOnlyDirty ?? false, // Save all lines, not just dirty ones
    },
  };

  // Use save/ directly — transaction/save/ has intermittent 404 issues.
  // save/ handles lines in the payload for header models (order, invoice, proposal, purchase).
  try {
    return await wcapiPost<any>("save/", body);
  } catch (err: any) {
    throw new Error(getBackendErrorMessage(err, "Failed to save transaction"));
  }
}

/**
 * Populate commission on a transaction from customer's rep assignments.
 * Calls the backend populate_transaction_commission service.
 * @param modelName - 'order', 'proposal', or 'invoice'
 * @param transactionId - PK of the transaction
 */
export async function populateCommission(
  modelName: string,
  transactionId: number,
): Promise<{ header_total: number; lines_updated: number; reps: any[] }> {
  const pluralMap: Record<string, string> = {
    order: 'orders', proposal: 'proposals', invoice: 'invoices',
  };
  const plural = pluralMap[modelName] || `${modelName}s`;
  const res = await apiClient.post<any>(
    `/tx/${plural}/${transactionId}/populate_commission/`,
  );
  return res.data;
}

export async function deleteRecord(model_name: string, id: number) {
  const resolved = resolveModelName(model_name);
  return wcapiPost<any>("delete/", { model_name: resolved, id });
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
    keyword: query,
  };
  if (options?.limit) {
    params.limit = options.limit;
  }
  return wcapiGet<GetListPayload>("get/", { params });
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
  config: {
    list: string[];
    detail: string[];
    views?: Array<{ name: string; list: string[]; detail: string[]; listWidths?: Record<string, number> }>;
  };
}

export async function getWorkbenchFieldsSetting(
  model_name: string,
): Promise<SettingRecord | null> {
  const data = await wcapiGet<GetListPayload>("get/", {
    params: {
      model_name: "setting",
      parent_model: model_name,
      purpose: "wc:workbench_fields",
    },
  });
  const results = data.results || [];
  return results.length > 0 ? results[0] : null;
}

export interface DetailFieldSettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  config: {
    hidden: string[];
    readOnly: string[];
  };
}

export interface SearchPresetRecord {
  id: number;
  name: string;
  role?: string | null;
  model_name: string;
  keyword?: string | null;
  search_fields?: string[] | null;
  filters?: Record<string, any> | null;
  ordering?: string | null;
  pagination?: Record<string, any> | null;
  request_keyword?: string | null;
  request_filters?: Record<string, { field: string; lookup?: string }> | null;
  relative_period?: { field: string; preset: string } | null;
  dt_modified?: number | null;
}

export type SearchPresetInputValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean>;

export interface RunSearchPresetOptions {
  values?: Record<string, SearchPresetInputValue>;
  params?: Record<string, any>;
  cacheExempt?: GetRecordsOptions["cacheExempt"];
}

function isIsoDateOnly(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value.trim());
}

function normalizePresetRequestValue(
  rawValue: SearchPresetInputValue,
  paramName: string,
  preset?: SearchPresetRecord,
): any {
  const normalized = normalizeSearchPresetValue(rawValue);

  if (typeof normalized !== "string") {
    return normalized;
  }

  const trimmed = normalized.trim();
  if (!trimmed) {
    return trimmed;
  }

  if (trimmed === "true") {
    return true;
  }
  if (trimmed === "false") {
    return false;
  }

  const requestSpec = preset?.request_filters?.[paramName];
  const requestField = requestSpec?.field || paramName;
  const lookup = requestSpec?.lookup || "exact";
  if (requestField.startsWith("dt_") && isIsoDateOnly(trimmed)) {
    const suffix = lookup === "lte" || paramName.toLowerCase().includes("end")
      ? "T23:59:59.999"
      : "T00:00:00.000";
    const timestamp = new Date(`${trimmed}${suffix}`).getTime();
    if (!Number.isNaN(timestamp)) {
      return timestamp;
    }
  }

  return trimmed;
}

function normalizeSearchPresetValue(value: SearchPresetInputValue): any {
  if (Array.isArray(value)) {
    return value.join(",");
  }
  return value;
}

function hasSearchPresetValue(value: SearchPresetInputValue): boolean {
  if (value == null) {
    return false;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  return true;
}

export function buildSearchPresetParams(
  preset: SearchPresetRecord,
  options?: RunSearchPresetOptions,
): Record<string, any> {
  const params = { ...(options?.params || {}) };
  const values = options?.values || {};

  if (preset.id != null) {
    params.saved_search_id ??= preset.id;
  } else if (preset.name) {
    params.saved_search ??= preset.name;
  }

  if (
    preset.request_keyword &&
    params.keyword == null &&
    params.search == null &&
    params.q == null
  ) {
    const keywordValue = values[preset.request_keyword];
    if (hasSearchPresetValue(keywordValue)) {
      params.keyword = normalizeSearchPresetValue(keywordValue);
    }
  }

  if (preset.request_filters) {
    Object.keys(preset.request_filters).forEach((paramName) => {
      if (params[paramName] != null) {
        return;
      }
      const rawValue = values[paramName];
      if (!hasSearchPresetValue(rawValue)) {
        return;
      }
      params[paramName] = normalizePresetRequestValue(
        rawValue,
        paramName,
        preset,
      );
    });
  }

  return params;
}

export async function runSearchPreset(
  model_name: string,
  preset: SearchPresetRecord,
  options?: RunSearchPresetOptions,
): Promise<GetListPayload> {
  const params = buildSearchPresetParams(preset, options);
  return getRecords(model_name, params, {
    cacheExempt: options?.cacheExempt,
  });
}

export async function getSearchPresets(
  model_name: string,
): Promise<SearchPresetRecord[]> {
  const resolved = resolveModelName(model_name);

  const data = await wcapiGet<{ results: SearchPresetRecord[] }>(
    "search-presets/",
    { params: { model_name: resolved } },
  );
  return data.results || [];
}

// Module-level cache for detail field settings to prevent duplicate API calls
const detailFieldSettingCache = new Map<
  string,
  DetailFieldSettingRecord | null
>();
const detailFieldSettingInFlight = new Map<
  string,
  Promise<DetailFieldSettingRecord | null>
>();

export async function getDetailFieldSetting(
  model_name: string,
): Promise<DetailFieldSettingRecord | null> {
  // Return cached result if available
  if (detailFieldSettingCache.has(model_name)) {
    return detailFieldSettingCache.get(model_name)!;
  }

  // Return existing in-flight promise if one exists
  if (detailFieldSettingInFlight.has(model_name)) {
    return detailFieldSettingInFlight.get(model_name)!;
  }

  // Create in-flight promise
  const fetchPromise = (async () => {
    try {
      const data = await wcapiGet<GetListPayload>("get/", {
        params: {
          model_name: "setting",
          parent_model: model_name,
          purpose: "detail_field_access",
        },
      });
      const results = data.results || [];
      const result =
        results.length > 0 ? (results[0] as DetailFieldSettingRecord) : null;
      detailFieldSettingCache.set(model_name, result);
      return result;
    } finally {
      detailFieldSettingInFlight.delete(model_name);
    }
  })();

  detailFieldSettingInFlight.set(model_name, fetchPromise);
  return fetchPromise;
}

/** Clear the detail field setting cache (call after saving settings) */
export function clearDetailFieldSettingCache(model_name?: string): void {
  if (model_name) {
    detailFieldSettingCache.delete(model_name);
  } else {
    detailFieldSettingCache.clear();
  }
}

export async function saveDetailFieldSetting(
  setting: DetailFieldSettingRecord,
) {
  const result = await wcapiPost<any>("save/", {
    ...setting,
    model_name: "setting",
  });
  clearDetailFieldSettingCache(setting.model_name);
  return result;
}

export async function getAllWorkbenchFieldsSettings(): Promise<
  SettingRecord[]
> {
  const data = await wcapiGet<GetListPayload>("get/", {
    params: { model_name: "setting", purpose: "wc:workbench_fields" },
  });
  return data.results || [];
}

export async function saveWorkbenchFieldsSetting(setting: SettingRecord) {
  return wcapiPost<any>("save/", { ...setting, model_name: "setting" });
}

/**
 * Call the /wcapi/_manage/ endpoint to run an administrative action.
 *
 * @param action  - The action name (e.g. "generate_kanban_projects")
 * @param params  - Action-specific parameters
 */
export async function manageAction(
  action: string,
  params: Record<string, any> = {},
) {
  return wcapiPost<any>("_manage/", { action, params });
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
    await apiClient.post("/wcapi/_refs_mismatch/", payload);
  } catch (err) {
    console.warn("[wcapi.logRefsMismatch] Failed to log mismatch:", err);
  }
}

// Document upload functions
export interface DocumentUploadResponse {
  document_id: number;
  path: string;
  checksum: string;
  is_duplicate: boolean;
  url: string;
  name: string;
  size_bytes: number;
  mime_type: string;
  document: any;
}

export async function uploadDocument(
  file: File,
  modelName?: string,
  parentId?: number,
  purpose: string = "attachment",
  description?: string,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (modelName) formData.append("model_name", modelName);
  if (parentId) formData.append("parent_id", parentId.toString());
  formData.append("purpose", purpose);
  if (description) formData.append("description", description);

  const response = await apiClient.post("/wcapi/upload/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  const raw = response.data as any;
  const payload = raw?.data ?? raw;
  const documentId = payload?.document_id ?? payload?.document?.id;

  if (!documentId) {
    throw new Error("Upload response missing document_id");
  }

  return {
    document_id: Number(documentId),
    path: payload?.path ?? "",
    checksum: payload?.checksum ?? "",
    is_duplicate: Boolean(payload?.is_duplicate),
    url: payload?.url ?? `/wcapi/document/${documentId}/`,
    name: payload?.name ?? file.name,
    size_bytes: Number(payload?.size_bytes ?? file.size),
    mime_type: payload?.mime_type ?? file.type,
    document: payload?.document ?? null,
  };
}

// ---------------------------------------------------------------------------
// Form Library — Andi/Alice is librarian, local checks out on demand
// ---------------------------------------------------------------------------

export interface FormLibraryEntry {
  id: number;
  uuid: string;
  ida: string;
  name: string;
  model_name: string;
  description: string;
  category: string;
  row_count: number;
  field_count: number;
  dt_modified: number;
  version: number;
}

export async function getFormLibrary(modelName: string): Promise<{ forms: FormLibraryEntry[]; total: number; source: string }> {
  const res = await apiClient.get('/wcapi/sync/form-library/', { params: { model: modelName, source: 'library' } });
  const payload = (res.data as any)?.data ?? res.data;
  return { forms: payload?.forms ?? [], total: payload?.total ?? 0, source: payload?.source ?? 'unknown' };
}

export async function checkoutForm(uuid: string, formData: any): Promise<any> {
  const res = await apiClient.post('/wcapi/sync/form-library/checkout/', { uuid, form_data: formData });
  return (res.data as any)?.data ?? res.data;
}

export async function submitFormToLibrary(reportId: number): Promise<any> {
  const res = await apiClient.post('/wcapi/sync/form-library/submit/', { report_id: reportId });
  return (res.data as any)?.data ?? res.data;
}

export async function restoreFormFromLibrary(reportId: number): Promise<any> {
  const res = await apiClient.post('/wcapi/sync/form-library/restore/', { report_id: reportId });
  return (res.data as any)?.data ?? res.data;
}
