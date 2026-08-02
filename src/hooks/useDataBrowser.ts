/**
 * useDataBrowser — all state and data management for the DataBrowser.
 *
 * Extracts: model selection, records fetch, search, sort, pagination,
 * field config, named layouts, subset filtering, CRUD, field behaviors.
 *
 * Reusable — any page that needs a model browser can call this hook.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams, useParams } from 'react-router-dom';
import { dbLog } from '@/utils/dbLog';
import {
  getModelNames,
  getModelDetail,
  getRecords,
  getRecord,
  saveRecord,
  deleteRecord,
  getWorkbenchFieldsSetting,
  saveWorkbenchFieldsSetting,
  getAllWorkbenchFieldsSettings,
} from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WorkbenchRecord = { id?: number | string; [key: string]: unknown };

/** Field specification — each field is an object with display properties */
export type FieldSpec = {
  field: string;
  width?: number;
  minWidth?: number;
  maxWidth?: number;
  color?: string | Record<string, string> | null;  // static, value-based map, or null
  align?: 'left' | 'center' | 'right';
  visible?: boolean;
  format?: 'currency' | 'percent' | 'date' | 'number' | 'json' | 'phone' | 'masked' | null;
  wrap?: boolean;  // true = word-wrap, false/undefined = truncate with ellipsis
  frozen?: boolean;
  summary?: 'sum' | 'avg' | 'count' | null;
  alice_note?: string;
  typeHint?: string;  // overrides auto-detected widget type from field_behaviors
};

// ---------------------------------------------------------------------------
// Smart defaults by field name — ported from wc2 listboxK._setColumnName
// ---------------------------------------------------------------------------
export function getDefaultFieldSpec(field: string): Partial<FieldSpec> {
  const fl = field.toLowerCase();

  // WHO fields — wider for names
  if (fl === 'display_name' || fl === 'company' || fl === 'name') return { width: 180, align: 'left' };
  if (fl === 'name_first' || fl === 'name_last') return { width: 120, align: 'left' };
  if (fl === 'attention') return { width: 140, align: 'left' };

  // Identifiers
  if (fl === 'ida' || fl === 'sku') return { width: 100, align: 'left' };
  if (fl === 'id') return { width: 60, align: 'right' };

  // Contact info
  if (fl.includes('phone')) return { width: 120, align: 'left', format: 'phone' };
  if (fl.includes('email')) return { width: 180, align: 'left' };
  if (fl.includes('zip') || fl.includes('postal')) return { width: 70, align: 'left' };
  if (fl === 'state' || fl === 'province') return { width: 60, align: 'center' };
  if (fl.includes('address') || fl === 'address_full') return { width: 220, align: 'left' };
  if (fl === 'city') return { width: 120, align: 'left' };
  if (fl === 'country') return { width: 80, align: 'center' };

  // Description / text
  if (fl === 'description' || fl === 'title') return { width: 220, align: 'left' };
  if (fl === 'notes' || fl === 'comments') return { width: 200, align: 'left', wrap: true };

  // Terms / level (must check before price pattern)
  if (fl === 'terms' || fl === 'price_level') return { width: 80, align: 'left' };

  // Currency / money
  if (fl.includes('price') || fl.includes('cost') || fl === 'total' || fl === 'balance'
    || fl === 'amount' || fl === 'debit' || fl === 'credit' || fl.includes('extended'))
    return { width: 100, align: 'right', format: 'currency' };

  // Rates / percentages
  if (fl.includes('rate') || fl === 'discount' || fl.includes('percent') || fl === 'commission')
    return { width: 80, align: 'right', format: 'percent' };

  // Weight
  if (fl.includes('weight') || fl.endsWith('_wt')) return { width: 60, align: 'right', format: 'number' };

  // Quantities
  if (fl === 'qty' || fl === 'quantity' || fl.startsWith('qty_') || fl === 'line_number' || fl === 'sequence')
    return { width: 60, align: 'right' };

  // Status / type / category
  if (fl === 'status' || fl === 'type' || fl === 'category' || fl === 'kind' || fl === 'org_type'
    || fl === 'kanban_column' || fl === 'priority')
    return { width: 100, align: 'left' };

  // Dates / timestamps
  if (fl.startsWith('dt_') || fl.includes('date') || fl.includes('_dt') || fl === 'deadline_by'
    || fl === 'start_by' || fl === 'end_by' || fl === 'expected_by' || fl === 'completed_by')
    return { width: 100, align: 'center', format: 'date' };

  // Booleans
  if (fl.startsWith('is_')) return { width: 50, align: 'center' };

  // Numeric scalars
  if (fl === 'version' || fl === 'security_level' || fl === 'health_rating' || fl === 'difficulty'
    || fl === 'burndown' || fl === 'linkage' || fl === 'count_accessed')
    return { width: 60, align: 'right' };

  // UUID
  if (fl === 'uuid') return { width: 100, align: 'left' };

  // JSON blobs — narrow in list (just show {…})
  if (fl === 'metadata' || fl === 'refs' || fl === 'prefs' || fl === 'actions' || fl === 'stats')
    return { width: 60, align: 'left', format: 'json' };

  // UOM
  if (fl === 'uom' || fl === 'unit_of_measure') return { width: 60, align: 'center' };

  // Source
  if (fl === 'source' || fl === 'source_model') return { width: 100, align: 'left' };

  // Default
  return {};
}

/** Apply smart defaults to a FieldSpec — user-set values always win */
export function applyFieldDefaults(spec: FieldSpec): FieldSpec {
  const defaults = getDefaultFieldSpec(spec.field);
  return {
    ...defaults,
    ...spec,
    // Only apply default width if user hasn't set one
    width: spec.width ?? defaults.width,
  };
}

/** Convert between string[] and FieldSpec[] — applies smart defaults */
export const toFieldSpecs = (fields: (string | FieldSpec)[]): FieldSpec[] =>
  fields.map((f) => typeof f === 'string'
    ? applyFieldDefaults({ field: f, visible: true })
    : applyFieldDefaults(f));

export const toFieldNames = (specs: (string | FieldSpec)[]): string[] =>
  specs.map((f) => typeof f === 'string' ? f : f.field);

export const toFieldWidths = (specs: FieldSpec[]): Record<string, number> => {
  const w: Record<string, number> = {};
  specs.forEach((s) => { if (s.width) w[s.field] = s.width; });
  return w;
};

export type NamedView = {
  name: string;
  list: (string | FieldSpec)[];
  detail: (string | FieldSpec)[];
  listWidths?: Record<string, number>;  // backward compat — prefer FieldSpec.width
};

export type WorkbenchFieldsSetting = {
  list: (string | FieldSpec)[];
  detail: (string | FieldSpec)[];
  views?: NamedView[];
};

export type SortSpec = { field: string; direction: 'asc' | 'desc' } | null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

const toRec = (v: unknown): WorkbenchRecord | null => (isObj(v) ? (v as WorkbenchRecord) : null);

const toRecList = (v: unknown): WorkbenchRecord[] =>
  Array.isArray(v) ? v.map(toRec).filter((r): r is WorkbenchRecord => r !== null) : [];

const fieldName = (f: unknown): string | null => {
  if (typeof f === 'string') return f;
  if (isObj(f) && typeof f['name'] === 'string') return f['name'] as string;
  return null;
};

export const numId = (v: unknown): number | null => {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') { const n = Number(v); return Number.isFinite(n) ? n : null; }
  return null;
};

export const errMsg = (e: unknown, fb: string): string => {
  if (e instanceof Error) return e.message;
  if (isObj(e) && typeof e['message'] === 'string') return e['message'] as string;
  return fb;
};

export const PAGE_SIZE = 50;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDataBrowser(isAuthenticated: boolean) {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeParams = useParams<{ model?: string }>();
  const previousModelParam = useRef<string | null>(null);

  // --- Model list ---
  const [modelNames, setModelNames] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState('');

  // --- Records ---
  const [records, setRecords] = useState<WorkbenchRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sort, setSort] = useState<SortSpec>(null);

  // --- Selection & detail ---
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<WorkbenchRecord | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // --- Subset filtering ---
  const [selectedRowIds, setSelectedRowIds] = useState<Set<number>>(new Set());
  const [subsetMode, setSubsetMode] = useState<'all' | 'show' | 'omit'>('all');

  // --- Fields ---
  const [allFields, setAllFields] = useState<string[]>([]);
  const [workbenchSetting, setWorkbenchSetting] = useState<WorkbenchFieldsSetting | null>(null);
  const [workbenchSettingsMap, setWorkbenchSettingsMap] = useState<Record<string, WorkbenchFieldsSetting>>({});
  // Track the Setting record id so we don't re-query on every save
  const [workbenchSettingId, setWorkbenchSettingId] = useState<number | null>(null);
  const workbenchSettingIdMap = useRef<Record<string, number>>({});

  // --- Named layouts ---
  const [activeViewName, setActiveViewName] = useState<string | null>(null);

  // --- Column state ---
  const [colWidths, setColWidths] = useState<Record<string, number>>({});

  // --- Field behaviors ---
  const [fieldBehaviors, setFieldBehaviors] = useState<Record<string, any>>({});
  const [fieldDefaults, setFieldDefaults] = useState<Record<string, any>>({});
  const [detailRowSizes, setDetailRowSizes] = useState<Record<string, number>>({});

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  // Route param (/db/:model) takes priority, then search param (?model=X), then pathname
  const pathnameModel = window.location.pathname.split('/').filter(Boolean)[0] || '';
  const modelParam = routeParams.model || searchParams.get('model') || pathnameModel;

  const modelLabel = useMemo(() => {
    if (!selectedModel) return 'Select model';
    const p = selectedModel.split('.');
    return p[p.length - 1] || selectedModel;
  }, [selectedModel]);

  // Raw field specs (may be strings or FieldSpec objects)
  const listFieldSpecs = useMemo((): FieldSpec[] => {
    if (workbenchSetting?.list?.length) return toFieldSpecs(workbenchSetting.list);
    const fallback = allFields.filter((f) => f !== 'id' && f !== 'uuid' && f !== 'version' && f !== 'is_deleted' && f !== 'is_archived' && f !== 'is_locked' && f !== 'security_level' && f !== 'search_vector').slice(0, 6);
    return toFieldSpecs(fallback.length ? fallback : ['ida']);
  }, [workbenchSetting?.list, allFields]);

  const detailFieldSpecs = useMemo((): FieldSpec[] => {
    if (workbenchSetting?.detail?.length) return toFieldSpecs(workbenchSetting.detail);
    return toFieldSpecs(allFields);
  }, [workbenchSetting?.detail, allFields]);

  // String arrays for components that need just field names (backward compat)
  const visibleListFields = useMemo(() => toFieldNames(listFieldSpecs.filter(s => s.visible !== false)), [listFieldSpecs]);
  const visibleDetailFields = useMemo(() => toFieldNames(detailFieldSpecs.filter(s => s.visible !== false)), [detailFieldSpecs]);

  // Column widths derived from field specs
  const specWidths = useMemo(() => toFieldWidths(listFieldSpecs), [listFieldSpecs]);

  const savedViews = useMemo(() => workbenchSetting?.views || [], [workbenchSetting?.views]);

  const totalPages = Math.max(1, Math.ceil(totalRecords / PAGE_SIZE));

  const displayRecords = useMemo(() => {
    if (subsetMode === 'show') return records.filter((r) => selectedRowIds.has(numId(r.id) ?? -1));
    if (subsetMode === 'omit') return records.filter((r) => !selectedRowIds.has(numId(r.id) ?? -1));
    return records;
  }, [records, subsetMode, selectedRowIds]);

  // ---------------------------------------------------------------------------
  // Model selection
  // ---------------------------------------------------------------------------

  const fetchingRef = useRef(false);
  const modelChangeRef = useRef(0); // monotonic counter to cancel stale fetches

  const instanceId = useRef(Math.random().toString(36).slice(2, 6));

  const handleSelectModel = useCallback((name: string) => {
    console.log('[DB]', instanceId.current, 'handleSelectModel', name);
    // Increment change counter — any in-flight fetch for old model will be discarded
    modelChangeRef.current += 1;
    fetchingRef.current = false;
    // Clear ALL state from previous model
    setRecords([]);
    setTotalRecords(0);
    setAllFields([]);
    setFieldBehaviors({});
    setWorkbenchSetting(null);
    setSelectedId(null);
    setSelectedRecord(null);
    setSelectedRowIds(new Set());
    setActiveViewName(null);
    setColWidths({});
    setPage(0);
    setActiveSearch(''); setSearchTerm('');
    setSort(null);
    setSubsetMode('all');
    setRecordsLoading(false);
    setRecordsError(null);
    // Set new model — this triggers the fetchRecords useEffect via dep change
    setSelectedModel(name);
    // Update URL
    const next = new URLSearchParams(searchParams);
    next.set('model', name);
    setSearchParams(next, { replace: true });
    previousModelParam.current = name;
  }, [searchParams, setSearchParams]);

  // Sync model FROM URL param (browser back/forward, external navigation, initial load ONLY)
  // This effect should NOT run when handleSelectModel changes the URL — previousModelParam guards that
  useEffect(() => {
    if (!modelNames.length) return;
    // URL param present and different from what we currently show — always switch
    if (modelParam && modelNames.includes(modelParam) && modelParam !== selectedModel) {
      // Only switch if this wasn't caused by handleSelectModel (which already set previousModelParam)
      if (modelParam !== previousModelParam.current) {
        console.log('[DB] URL sync: switching to', modelParam);
        previousModelParam.current = modelParam;
        setSelectedModel(modelParam);
        return;
      }
    }
    // No model selected yet and no URL param — default to first model
    if (!selectedModel && !modelParam) {
      console.log('[DB] URL sync: no model, defaulting to', modelNames[0]);
      setSelectedModel(modelNames[0]);
      previousModelParam.current = modelNames[0];
    }
  }, [modelNames, modelParam, selectedModel]); // include selectedModel to detect stale state

  // ---------------------------------------------------------------------------
  // Load models
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!isAuthenticated) return;
    (async () => {
      try {
        setLoadingModels(true); setModelsError(null);
        const data = await getModelNames();
        setModelNames((Array.isArray(data.model_names) ? data.model_names : []).slice().sort((a, b) => a.localeCompare(b)));
        const settings = await getAllWorkbenchFieldsSettings();
        const map: Record<string, WorkbenchFieldsSetting> = {};
        settings.forEach((s: any) => { map[s.parent_model || s.model_name] = s.config; });
        setWorkbenchSettingsMap(map);
      } catch (e) { setModelsError(errMsg(e, 'Failed to load models')); }
      finally { setLoadingModels(false); }
    })();
  }, [isAuthenticated]);

  // ---------------------------------------------------------------------------
  // Fetch records
  // ---------------------------------------------------------------------------

  const fetchRecords = useCallback(async () => {
    if (!selectedModel || (modelNames.length && !modelNames.includes(selectedModel))) return;
    const fetchId = modelChangeRef.current;
    console.log('[DB]', instanceId.current, 'fetchRecords', selectedModel, 'fetchId=', fetchId);
    fetchingRef.current = true;
    try {
      setRecordsLoading(true); setRecordsError(null);
      const md = await getModelDetail(selectedModel) as { model?: { fields?: unknown } };
      if (modelChangeRef.current !== fetchId) { dbLog('fetchRecords:stale (model changed)'); return; }

      const rf = md?.model?.fields;
      let fields: string[] = [];
      if (Array.isArray(rf)) fields = rf.map(fieldName).filter((n): n is string => !!n);
      else if (isObj(rf)) fields = Object.keys(rf);
      setAllFields(fields);
      dbLog('fetchRecords:fields', { model: selectedModel, fieldCount: fields.length, fields: fields.slice(0, 10) });

      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
      if (activeSearch.trim()) params.keyword = activeSearch.trim();
      if (sort) params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field;

      const list = await getRecords(selectedModel, params) as { results?: unknown; total?: number };
      if (modelChangeRef.current !== fetchId) { dbLog('fetchRecords:stale (model changed)'); return; }

      const resultList = toRecList(list?.results);
      const resultTotal = typeof list?.total === 'number' ? list.total : resultList.length;
      console.log('[DB]', instanceId.current, 'setRecords', selectedModel, resultTotal, 'records, fetchId=', fetchId);
      setRecords(resultList);
      setTotalRecords(resultTotal);

      // Log search to Alice for pattern detection (fire and forget)
      if (activeSearch.trim()) {
        import('@/api/wcapi').then(({ manageAction }) => {
          const uid = typeof window !== 'undefined' && (window as any).__WC_USER_ID;
          if (uid) manageAction('log_user_search', { contact_id: uid, model: selectedModel, search_term: activeSearch.trim(), result_count: resultTotal }).catch(() => {});
        }).catch(() => {});
      }

      // Load workbench setting directly (not from cached map — avoids stale closure)
      let ws: WorkbenchFieldsSetting | null = null;
      let wsId: number | null = null;
      try {
        const wsRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'workbench_fields', limit: 1 }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const wsRec = (wsRes?.results || [])[0];
        ws = wsRec?.config || null;
        wsId = wsRec?.id ?? null;
      } catch { /* use null */ }
      setWorkbenchSetting(ws);
      setWorkbenchSettingId(wsId);
      if (wsId && selectedModel) workbenchSettingIdMap.current[selectedModel] = wsId;
      dbLog('fetchRecords:workbenchSetting', { model: selectedModel, settingId: wsId, list: ws?.list?.slice(0, 8), detail: ws?.detail?.slice(0, 8), views: ws?.views?.length });

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'field_access' }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const faRec = (faRes?.results || [])[0];
        setFieldBehaviors(faRec?.config?.field_behaviors || {});
        setFieldDefaults(faRec?.prefs?.defaults || {});
      } catch { setFieldBehaviors({}); setFieldDefaults({}); }
    } catch (e) {
      if (modelChangeRef.current !== fetchId) return; // don't show error for stale fetch
      const msg = errMsg(e, 'Failed to load records');
      setRecordsError(msg);
      dbLog.error('fetchRecords:failed', { model: selectedModel, error: msg });
    }
    finally { setRecordsLoading(false); fetchingRef.current = false; }
  }, [selectedModel, modelNames, page, activeSearch, sort]);
  // NOTE: workbenchSettingsMap intentionally excluded — it changes when layouts are saved,
  // which would cause infinite re-fetch. We read it inside fetchRecords via closure.

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  // Debounced search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => { setActiveSearch(searchTerm); setPage(0); }, 400);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [searchTerm]);

  // Load detail + broadcast selection to other windows (JSON Viewer, spawn windows)
  useEffect(() => {
    if (!selectedModel || selectedId == null) return;
    (async () => {
      const d = await getRecord(selectedModel, selectedId) as { record?: unknown };
      setSelectedRecord(toRec(d?.record));
      setIsDirty(false);
      // Notify other windows
      import('@/utils/windowChannel').then(({ windowChannel }) => {
        windowChannel.send({ type: 'record-selected', model: selectedModel, id: selectedId });
      }).catch(() => {});
    })();
  }, [selectedModel, selectedId]);

  // ---------------------------------------------------------------------------
  // Field operations
  // ---------------------------------------------------------------------------

  const updateField = useCallback((f: string, v: unknown) => { setSelectedRecord((p) => p ? { ...p, [f]: v } : p); setIsDirty(true); }, []);

  const persistSetting = useCallback(async (model: string, next: WorkbenchFieldsSetting) => {
    const settingId = workbenchSettingIdMap.current[model];
    const listPreview = (next.list || []).slice(0, 4).map(f => typeof f === 'string' ? f : f.field);
    console.log('[DB] persistSetting', model, 'settingId:', settingId, 'list:', listPreview, 'views:', (next.views || []).map(v => v.name));
    const { saveRecord } = await import('@/api/wcapi');

    const maxRetries = 5;
    const retryDelay = 1500; // ms

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        if (settingId) {
          // Surgical update: send each piece separately using dot-path ops
          // config.list and config.detail update in place; views upsert by name
          const ops: Record<string, any> = {
            id: settingId,
            'config.list': { mode: 'update', value: next.list || [] },
            'config.detail': { mode: 'update', value: next.detail || [] },
          };
          // Upsert each named view individually
          for (const view of (next.views || [])) {
            if (view.name) {
              ops[`config.views`] = { mode: 'upsert', key: 'name', value: view };
            }
          }
          await saveRecord('setting', ops);
        } else {
          const result = await saveRecord('setting', {
            name: `workbench_fields:${model}`,
            parent_model: model,
            purpose: 'workbench_fields',
            config: next,
          });
          const newId = result?.id || result?.data?.id || result?.data?.record?.id;
          if (newId) workbenchSettingIdMap.current[model] = newId;
        }
        console.log('[DB] persistSetting saved:', settingId || 'new');
        return; // success
      } catch (e: any) {
        const msg = e?.response?.data?.message || e?.message || '';
        const isLocked = msg.toLowerCase().includes('locked') ||
          e?.response?.data?.error?.code === 'record_locked' ||
          e?.response?.status === 423;

        if (isLocked && attempt < maxRetries) {
          console.warn(`[DB] Setting #${settingId} locked, retry ${attempt}/${maxRetries} in ${retryDelay}ms`);
          await new Promise(r => setTimeout(r, retryDelay));
          continue;
        }

        if (isLocked) {
          console.error(`[DB] Setting #${settingId} locked after ${maxRetries} retries — changes not saved`);
          alert(`Layout changes could not be saved — the Setting record (#${settingId}) is locked by another process. Your changes are visible but will not persist on reload. Try again in a moment.`);
        } else {
          console.error('[DB] Save layout failed:', model, e);
        }
        return;
      }
    }
  }, []);

  const toggleField = useCallback(async (kind: 'list' | 'detail', field: string) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const base = cur[kind]?.length ? cur[kind] : (kind === 'list' ? visibleListFields : allFields);
    const updated = base.includes(field) ? base.filter((f: string) => f !== field) : [...base, field];
    const next: WorkbenchFieldsSetting = { ...cur, [kind]: updated };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, visibleListFields, allFields, persistSetting]);

  const bulkSetFields = useCallback(async (kind: 'list' | 'detail', mode: 'all' | 'clear') => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const next: WorkbenchFieldsSetting = { ...cur, [kind]: mode === 'all' ? allFields : [] };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, allFields, persistSetting]);

  // Sort
  const handleSort = useCallback((field: string) => {
    setSort((p) => {
      if (p?.field === field) return p.direction === 'asc' ? { field, direction: 'desc' } : null;
      return { field, direction: 'asc' };
    });
    setPage(0);
  }, []);

  // Column drag reorder
  const handleColumnDrop = useCallback((dragField: string, target: string) => {
    if (!dragField || dragField === target) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const list = [...(cur.list?.length ? cur.list : visibleListFields)];
    const fi = list.indexOf(dragField), ti = list.indexOf(target);
    if (fi < 0 || ti < 0) return;
    list.splice(fi, 1); list.splice(ti, 0, dragField);
    const next: WorkbenchFieldsSetting = { ...cur, list };
    setWorkbenchSetting(next); setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    persistSetting(selectedModel, next);
  }, [workbenchSetting, visibleListFields, selectedModel, persistSetting]);

  // Column resize
  const resizingRef = useRef<{ field: string; startX: number; startW: number } | null>(null);
  const handleResizeStart = useCallback((field: string, e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    resizingRef.current = { field, startX: e.clientX, startW: colWidths[field] || 120 };
    const onMove = (ev: MouseEvent) => {
      if (!resizingRef.current) return;
      const newW = resizingRef.current!.startW + ev.clientX - resizingRef.current!.startX;
      setColWidths((p) => ({ ...p, [resizingRef.current!.field]: Math.max(12, newW) }));
    };
    const onUp = () => {
      resizingRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      // Auto-save widths to the setting — update FieldSpec widths
      if (selectedModel) {
        setColWidths((latestWidths) => {
          const cur = workbenchSetting ?? { list: [], detail: [] };
          const updatedList = toFieldSpecs(cur.list || []).map(s => ({
            ...s,
            width: latestWidths[s.field] ?? s.width,
          }));
          const next = { ...cur, list: updatedList };
          setWorkbenchSetting(next);
          persistSetting(selectedModel, next).catch(() => {});
          return latestWidths;
        });
      }
    };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  }, [colWidths, selectedModel, workbenchSetting, persistSetting]);

  // ---------------------------------------------------------------------------
  // Layouts
  // ---------------------------------------------------------------------------

  const saveView = useCallback(async (name: string, fields?: (string | FieldSpec)[], mode?: 'list' | 'detail') => {
    if (!selectedModel || !name.trim()) return;
    if (PROTECTED_VIEWS.includes(name.trim().toLowerCase())) {
      alert(`"${name}" is a system layout and cannot be overwritten.`);
      return;
    }
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const views = [...(cur.views || [])];
    const idx = views.findIndex((v) => v.name === name.trim());
    // Convert fields to FieldSpec objects, merge with current column widths
    const specs = fields ? toFieldSpecs(fields).map(s => ({
      ...s,
      width: s.width || colWidths[s.field] || undefined,
    })) : undefined;
    // Only update the side (list or detail) that changed — preserve the other
    const listSpecs = (mode === 'list' && specs) ? specs : cur.list || [];
    const detailSpecs = (mode === 'detail' && specs) ? specs : cur.detail || [];
    const view: NamedView = { name: name.trim(), list: listSpecs, detail: detailSpecs, listWidths: { ...colWidths } };
    if (idx >= 0) views[idx] = view; else views.push(view);
    const next: WorkbenchFieldsSetting = { ...cur, list: listSpecs, detail: detailSpecs, views };
    setWorkbenchSetting(next); setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    setActiveViewName(name.trim());
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, colWidths, persistSetting]);

  const loadView = useCallback(async (v: NamedView) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const next: WorkbenchFieldsSetting = { ...cur, list: v.list, detail: v.detail };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    setColWidths(v.listWidths || {}); setActiveViewName(v.name);
    // Persist so the active layout survives reload
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, persistSetting]);

  // Reset layout — load the 'initial' or 'alice_guess' view as a baseline
  const resetLayout = useCallback(async () => {
    if (!selectedModel) return;
    if (!confirm('Reset to default layout? Your current layout will be replaced.')) return;
    const cur = workbenchSetting ?? { list: [], detail: [], views: [] };
    const views = cur.views || [];
    const initial = views.find((v) => v.name === 'initial') || views.find((v) => v.name === 'alice_guess');
    if (initial) {
      const next: WorkbenchFieldsSetting = { ...cur, list: initial.list, detail: initial.detail };
      setWorkbenchSetting(next);
      setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
      setColWidths(initial.listWidths || {});
      setActiveViewName(initial.name);
      await persistSetting(selectedModel, next);
    }
  }, [selectedModel, workbenchSetting, persistSetting]);

  const deleteView = useCallback(async (name: string) => {
    if (!selectedModel || !confirm(`Delete layout "${name}"?`)) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const next: WorkbenchFieldsSetting = { ...cur, views: (cur.views || []).filter((v) => v.name !== name) };
    setWorkbenchSetting(next); setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    if (activeViewName === name) setActiveViewName(null);
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, activeViewName, persistSetting]);

  // Row selection
  const toggleRow = useCallback((id: number) => setSelectedRowIds((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; }), []);
  const selectAllRows = useCallback(() => setSelectedRowIds(new Set(records.map((r) => numId(r.id)).filter((n): n is number => n !== null))), [records]);

  // CSV export
  const exportCSV = useCallback(() => {
    const fields = visibleListFields;
    const lines = [fields.join(','), ...displayRecords.map((r) =>
      fields.map((f) => { const s = typeof r[f] === 'object' && r[f] !== null ? JSON.stringify(r[f]) : String(r[f] ?? ''); return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s; }).join(',')
    )];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `${selectedModel || 'export'}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(a.href);
  }, [displayRecords, visibleListFields, selectedModel]);

  // Validation errors — field-keyed dict, empty = valid
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Save record — validate first, accumulate all errors
  const handleSaveRecord = useCallback(async () => {
    if (!selectedModel || !selectedRecord) return;
    // Client-side validation (accumulates all errors, does not stop at first)
    const { validateRecord, hasErrors } = await import('@/utils/validateRecord');
    const errors = validateRecord(selectedRecord, fieldBehaviors, visibleDetailFields);
    setValidationErrors(errors);
    if (hasErrors(errors)) return;
    try {
      await saveRecord(selectedModel, { ...selectedRecord });
      setIsDirty(false); setValidationErrors({}); fetchRecords();
      // Notify other windows
      import('@/utils/windowChannel').then(({ windowChannel }) => {
        windowChannel.send({ type: 'record-saved', model: selectedModel, id: selectedId ?? undefined });
      }).catch(() => {});
    } catch (e) {
      // Surface server-side validation errors
      const msg = errMsg(e, 'Save failed');
      dbLog.error('handleSaveRecord:failed', { model: selectedModel, error: msg });
    }
  }, [selectedModel, selectedRecord, fieldBehaviors, visibleDetailFields, fetchRecords]);

  // Delete record — doSafeSelect: auto-select adjacent record after delete
  const handleDeleteRecord = useCallback(async () => {
    if (!selectedModel || !selectedId || !confirm(`Delete ${modelLabel} #${selectedId}?`)) return;
    await deleteRecord(selectedModel, selectedId);
    const idx = records.findIndex((r) => numId(r.id) === selectedId);
    const filtered = records.filter((r) => numId(r.id) !== selectedId);
    setRecords(filtered);
    const nextIdx = Math.min(idx, filtered.length - 1);
    if (nextIdx >= 0) {
      const next = filtered[nextIdx];
      setSelectedId(numId(next.id));
      setSelectedRecord(next);
    } else {
      setSelectedRecord(null);
      setSelectedId(null);
    }
  }, [selectedModel, selectedId, modelLabel, records]);

  // Protected layouts — never overwrite these
  const PROTECTED_VIEWS = ['alice_guess', 'alphabetical', 'alpha', 'best_guess'];

  // Update list fields — persists to data.list (survives reload) but does NOT touch named views.
  // User must explicitly Save/Save As to commit to a named view.
  const updateListLayout = useCallback(async (fields: (string | FieldSpec)[]) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const specs = toFieldSpecs(fields).map(s => ({
      ...s, width: s.width || colWidths[s.field] || undefined,
    }));
    const next: WorkbenchFieldsSetting = { ...cur, list: specs };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, colWidths, persistSetting]);

  // Update detail fields — persists to data.detail but does NOT touch named views.
  const updateDetailLayout = useCallback(async (fields: (string | FieldSpec)[], sizes: Record<string, number>) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const specs = toFieldSpecs(fields);
    const next: WorkbenchFieldsSetting = { ...cur, detail: specs };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    setDetailRowSizes(sizes);
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, colWidths, persistSetting]);

  return {
    // Model
    modelNames, loadingModels, modelsError, selectedModel, modelLabel, modelParam,
    handleSelectModel,
    // Records
    records, setRecords, recordsLoading, recordsError, totalRecords, setTotalRecords, page, setPage, totalPages,
    displayRecords, fetchRecords,
    // Search
    searchTerm, setSearchTerm,
    // Sort
    sort, handleSort,
    // Selection
    selectedId, setSelectedId, selectedRecord, setSelectedRecord, isDirty, setIsDirty,
    selectedRowIds, setSelectedRowIds, subsetMode, setSubsetMode,
    toggleRow, selectAllRows,
    // Fields
    allFields, visibleListFields, visibleDetailFields,
    listFieldSpecs, detailFieldSpecs, specWidths,
    workbenchSetting, toggleField, bulkSetFields,
    // Layouts
    savedViews, activeViewName, saveView, loadView, deleteView, resetLayout,
    workbenchSettingId,
    // Columns
    colWidths, setColWidths, handleColumnDrop, handleResizeStart,
    // Field behaviors
    fieldBehaviors, fieldDefaults, detailRowSizes, setDetailRowSizes,
    // CRUD
    updateField, handleSaveRecord, handleDeleteRecord, validationErrors,
    updateListLayout,
    updateDetailLayout,
    // Export
    exportCSV,
  };
}
