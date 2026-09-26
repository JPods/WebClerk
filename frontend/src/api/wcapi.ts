/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import apiClient from "./axios";
import { resolveModelName } from "./modelNameResolver";
import { validateEnvelope } from "../utils/validateEnvelope";
import { MAX_PAYLOAD_BYTES } from "../constants/envelopeLimits";
import { computeAthenaToken } from "../utils/athenaToken";

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

/** A refusal as the door answers it: HTTP status, the door's code, its coaching sentence,
 *  and the details. The sentence is `message`; `error` is an object and never shown raw. */
export interface Refusal {
  status: number | null;
  code: string | null;
  message: string;
  details: unknown;
}

export function refusedFrom(err: any, fallback = 'Request failed'): Refusal {
  const data = err?.response?.data;
  const error = data?.error;
  const message =
    (typeof data?.message === 'string' && data.message) ||
    (typeof data === 'string' && data) ||
    (typeof error === 'string' && error) ||
    err?.message ||
    fallback;
  const details = error && typeof error === 'object' ? error.details : undefined;
  // Some answers carry only a label in `message` ("Invalid field values") and the cause
  // in details — a string, or {field: [msgs]}. Name the cause unless the sentence already does.
  const cause = describeDetails(details);
  return {
    status: err?.response?.status ?? null,
    code: (error && typeof error === 'object' && error.code) || null,
    message: cause && !message.includes(cause) ? `${message}: ${cause}` : message,
    details,
  };
}

function describeDetails(details: unknown): string {
  if (typeof details === 'string') return details;
  if (Array.isArray(details)) return details.filter((d) => typeof d === 'string').join('; ');
  if (details && typeof details === 'object') {
    return Object.entries(details as Record<string, unknown>)
      .map(([field, v]) => `${field}: ${Array.isArray(v) ? v.join(', ') : String(v)}`)
      .join('; ');
  }
  return '';
}

function getBackendErrorMessage(err: any, fallback: string): string {
  const data = err?.response?.data;
  if (!data) {
    return err?.message || fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  const detail = data?.detail;

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

  if (typeof detail === 'string' && detail) return detail;
  return refusedFrom(err, fallback).message;
}

/**
 * The REST channel lives at /wcapi/ — one mount, no fallback.
 */
async function wcapiGet<T>(path: string, config?: any): Promise<T> {
  const res = await apiClient.get<ApiEnvelope<T>>(`/wcapi/${path}`, config);
  return res.data.data;
}

async function wcapiPost<T>(path: string, body: any, extraHeaders?: Record<string, string>): Promise<T> {
  const config = extraHeaders ? { headers: extraHeaders } : undefined;
  const res = await apiClient.post<ApiEnvelope<T>>(`/wcapi/${path}`, body, config);
  return res.data.data;
}

/**
 * The REST channel (Bill, 2026-09-24: REST only). The path names the model and the record;
 * the HTTP method names the verb:
 *   POST /wcapi/<model>/ creates · PUT /wcapi/<model>/<id>/ updates · DELETE /wcapi/<model>/<id>/
 */
export function recordPath(model: string, id?: number | string | null): string {
  return id !== undefined && id !== null && id !== '' ? `/wcapi/${model}/${id}/` : `/wcapi/${model}/`;
}

export async function wcapiSave<T>(model: string, body: any, extraHeaders?: Record<string, string>,
                                   recordId?: number | string): Promise<T> {
  // REST only (2026-09-24): the model and the id are the path; the body is the fields, flat.
  const config = extraHeaders ? { headers: extraHeaders } : undefined;
  const id = recordId ?? body?.id;
  const res = id
    ? await apiClient.put<ApiEnvelope<T>>(recordPath(model, id), body, config)
    : await apiClient.post<ApiEnvelope<T>>(recordPath(model), body, config);
  return res.data.data;
}

// ---------------------------------------------------------------------------
// PJPV schema field metadata — cached in memory for the session
// ---------------------------------------------------------------------------

/**
 * Field metadata from Pydantic schemas (served by /wcapi/_pjpv_fields/).
 * Maps envelope.field → {widget, type, label, precision, ...}
 */
export type PjpvFieldMeta = {
  type: string;
  label: string;
  widget: string;        // 'currency' | 'percent' | 'number' | 'text' | ...
  precision?: number;
  readonly?: boolean;
  description?: string;
  min?: number;
  max?: number;
  selectlist_key?: string;  // key into SELECT_LIST_MAP for select widgets
};

export type PjpvCatalog = Record<string, Record<string, PjpvFieldMeta>>;

let _pjpvCache: PjpvCatalog | null = null;
let _pjpvPromise: Promise<PjpvCatalog> | null = null;

/**
 * Fetch the full PJPV field catalog.  Cached — only one network call per
 * session.  Returns {envelopeName: {fieldName: PjpvFieldMeta}}.
 *
 * The schema endpoint is public (AllowAny) so this works even before login.
 */
export async function getPjpvFieldsCatalog(): Promise<PjpvCatalog> {
  if (_pjpvCache) return _pjpvCache;
  if (_pjpvPromise) return _pjpvPromise;

  _pjpvPromise = (async () => {
    try {
      // System dispatch endpoint — returns raw JSON, not ApiEnvelope
      const res = await apiClient.get('/wcapi/_pjpv_fields/');
      const data = res.data;
      _pjpvCache = data?.envelopes || {};
      return _pjpvCache!;
    } catch {
      console.warn('[PJPV] Schema endpoint unavailable — name-guessing only');
      _pjpvCache = {};
      return _pjpvCache;
    } finally {
      _pjpvPromise = null;
    }
  })();

  return _pjpvPromise;
}

/**
 * Build a flat lookup: "envelope.field" → PjpvFieldMeta from the catalog.
 * Also includes bare field names for top-level matches.
 */
export function flattenPjpvCatalog(catalog: PjpvCatalog): Record<string, PjpvFieldMeta> {
  const flat: Record<string, PjpvFieldMeta> = {};
  for (const [envelope, fields] of Object.entries(catalog)) {
    for (const [field, meta] of Object.entries(fields)) {
      flat[`${envelope}.${field}`] = meta;
      // Bare field name — first writer wins (envelope-qualified takes priority at lookup)
      if (!flat[field]) flat[field] = meta;
    }
  }
  return flat;
}

export async function getModelNames() {
  return wcapiGet<ModelNamesPayload>("_model_list/");
}

export async function getModelDetail(model_name: string) {
  const resolved = resolveModelName(model_name);
  return wcapiGet<ModelDetailPayload>("_model_detail/", {
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
  return wcapiGet<GetListPayload>(`${resolved}/`, {
    params: { ...normalizedParams },
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

/** Cached time-billing service items (purpose=time-billing). Rarely changes. */
export async function getTimeBillingItems(): Promise<any[]> {
  const cacheKey = 'item:time-billing';
  const cached = optionCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < OPTION_CACHE_TTL) {
    return cached.data as any;
  }
  const resp: any = await getRecords('item', { purpose: 'time-billing', kind: 'service', limit: 50 });
  const items = resp?.results || resp?.items || resp?.records || [];
  optionCache.set(cacheKey, { data: items, timestamp: Date.now() });
  return items;
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
  return wcapiGet<GetDetailPayload>(`${resolved}/${id}/`, {
    cache: false,
  } as any);
}

export async function saveRecord(model_name: string, payload: any) {
  const resolved = resolveModelName(model_name);
  // id goes in the path; mode is not a REST concept (PUT and PATCH merge) — neither is sent.
  const { id, mode: _mode, ...record } = payload;
  // Strip computed property fields that don't exist as model columns — they cause
  // envelope_invalid errors when the backend tries to pack them into config.
  // These are @property methods on TransactionBaseModel, not real DB fields.
  for (const k of ['email', 'phone', 'address_full', 'company_name']) {
    delete record[k];
  }

  // ── Pre-flight: envelope validation ──
  const envelopeErrors = validateEnvelope(record);
  if (envelopeErrors.length > 0) {
    const messages = envelopeErrors.map(e => `${e.path}: ${e.message}`);
    throw new Error(`Validation failed: ${messages.join('; ')}`);
  }

  // The fields go flat: no `record` wrapper, no model_name, no id, no mode in the body.
  // The door does not unwrap `record` and drops unknown keys, so the wrapped form returned
  // success and saved nothing (Fable bottom-up L5 H-1, 2026-09-25). PUT and PATCH merge.
  const body: any = { ...record };

  // ── Pre-flight: payload size check ──
  const serialized = JSON.stringify(body);
  if (serialized.length > MAX_PAYLOAD_BYTES) {
    throw new Error(
      `Payload too large (${(serialized.length / 1024).toFixed(0)} KB) — ` +
      `maximum ${(MAX_PAYLOAD_BYTES / 1024 / 1024).toFixed(0)} MB`
    );
  }

  // ── Athena: sign validated payload ──
  const athenaToken = await computeAthenaToken(serialized);

  try {
    const headers: Record<string, string> = {};
    if (athenaToken) {
      headers['X-Athena-Validated'] = athenaToken;
    }
    return await wcapiSave<any>(resolved, body, headers, id);
  } catch (err: any) {
    throw new Error(getBackendErrorMessage(err, "Save failed"));
  }
}

/**
 * Save a document (order, invoice, quote, purchase, workorder) with its lines — the REST
 * save like any other record: PUT /wcapi/<model>/<id>/ or POST /wcapi/<model>/. The lines
 * ride in `lines`; a removed line carries `_delete: true`. Totals are the server's.
 */
export async function saveTransactionWithLines(model_name: string, payload: any) {
  const resolved = resolveModelName(model_name);
  // Strip read-only and calculated fields — only send what the server needs
  const headerStripKeys = [
    'uuid', 'customer_config', 'customer_company',
    'totals', 'actions', 'refs', 'metadata',
    // finance stays: it carries the tax jurisdiction and rate the user chose.
    'sell', 'cost', 'flow',
    'prefs', 'commission', 'health_rating',
    'dt_created', 'dt_modified',
    'is_archived', 'is_locked',
    'security_level', 'version',
  ];
  const lineStripKeys = [
    // 'tax' stays: a rate typed on a line is the user's input (recheck 2).
    // 'totals' is stripped: line results belong to the server's totals engine.
    // '_removed' is the local display flag and never goes over the wire;
    // '_delete' DOES — it is how the backend is told to delete that row.
    '_removed',
    'uuid', 'metadata', 'prefs',
    'physical', 'actions', 'totals',
    'dt_created', 'dt_modified', 'health_rating',
    'is_archived', 'is_locked',
    'security_level', 'version',
  ];
  const cleanPayload = Object.fromEntries(
    Object.entries(payload).filter(([k]) => !headerStripKeys.includes(k)),
  );
  // Strip read-only/calculated fields from lines too
  if (Array.isArray(cleanPayload.lines)) {
    cleanPayload.lines = cleanPayload.lines.map((line: any) => {
      return Object.fromEntries(
        Object.entries(line).filter(([k]) => !lineStripKeys.includes(k)),
      );
    });
  }
  const { id: docId, model_name: _model, mode: _mode, ...docFields } = cleanPayload;
  const body = docFields;                                   // flat: model and id are the path

  try {
    return await wcapiSave<any>(resolved, body, undefined, docId);
  } catch (err: any) {
    throw new Error(getBackendErrorMessage(err, "Failed to save transaction"));
  }
}

/**
 * Populate commission on a transaction from customer's rep assignments.
 * Calls the backend populate_transaction_commission service.
 * @param modelName - 'order', 'quote', or 'invoice'
 * @param transactionId - PK of the transaction
 */
export async function populateCommission(
  modelName: string,
  transactionId: number,
): Promise<{ header_total: number; lines_updated: number; reps: any[] }> {
  const pluralMap: Record<string, string> = {
    order: 'orders', quote: 'quotes', invoice: 'invoices',
  };
  const plural = pluralMap[modelName] || `${modelName}s`;
  const res = await apiClient.post<any>(
    `/tx/${plural}/${transactionId}/populate_commission/`,
  );
  return res.data;
}

export async function deleteRecord(model_name: string, id: number) {
  const resolved = resolveModelName(model_name);
  const res = await apiClient.delete<ApiEnvelope<any>>(recordPath(resolved, id));
  return res.data.data;
}

/**
 * Search for items by query string (sku, name, description, etc.)
 */
export async function searchItems(
  query: string,
  options?: { limit?: number },
): Promise<GetListPayload> {
  const params: any = {
    keyword: query,
  };
  if (options?.limit) {
    params.limit = options.limit;
  }
  return wcapiGet<GetListPayload>("item/", { params });
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
  const data = await wcapiGet<GetListPayload>("setting/", {
    params: {
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
    "_search_presets/",
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
      const data = await wcapiGet<GetListPayload>("setting/", {
    params: {
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
  const result = await wcapiSave<any>("setting", {
    ...setting,
    model_name: "setting",
  });
  clearDetailFieldSettingCache(setting.model_name);
  return result;
}

export async function getAllWorkbenchFieldsSettings(): Promise<
  SettingRecord[]
> {
  const data = await wcapiGet<GetListPayload>("setting/", {
    params: { purpose: "wc:workbench_fields" },
  });
  return data.results || [];
}

export async function saveWorkbenchFieldsSetting(setting: SettingRecord) {
  return wcapiSave<any>("setting", { ...setting, model_name: "setting" });
}

/**
 * Call the /wcapi/_manage/ endpoint to run an administrative action.
 *
 * @param action  - The action name (e.g. "generate_kanban_projects")
 * @param params  - Action-specific parameters
 */
/**
 * Forward a record to WC HQ. The server holds the Athena token and relays it.
 */
export async function submitToWchq(model_name: string, record: Record<string, unknown>) {
  try {
    return await wcapiPost<any>("_wchq_submit/", { model_name, record });
  } catch (err: any) {
    throw new Error(getBackendErrorMessage(err, "WC HQ submit failed"));
  }
}

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

/**
 * Resolve three-tier selectlists for a specific record.
 * Returns: {selectlists: {field: {options, source, source_detail}}, ...}
 *
 * Three-tier inheritance (most specific wins):
 *   1. Model-level Setting selectlists
 *   2. record.config.selectlist_profile → Setting selectlists
 *   3. record.config.selectlists (inline on the record)
 */
export interface ResolvedSelectList {
  options: { value: string; label: string }[];
  source: 'model' | 'profile' | 'record';
  source_detail: string;
}

export async function getResolvedSelectlists(
  modelName: string,
  recordId: number,
): Promise<Record<string, ResolvedSelectList>> {
  try {
    const res = await apiClient.get('/wcapi/_selectlists/', {
      params: { model_name: modelName, record_id: recordId },
    });
    const data = res.data;
    return data?.selectlists ?? {};
  } catch {
    return {};
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
    url: payload?.url ?? `/wcapi/document/${documentId}/download/`,
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
