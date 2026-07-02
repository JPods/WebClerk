/**
 * useDataBrowser — all state and data management for the DataBrowser.
 *
 * Extracts: model selection, records fetch, search, sort, pagination,
 * field config, named layouts, subset filtering, CRUD, field behaviors.
 *
 * Reusable — any page that needs a model browser can call this hook.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
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

export type NamedView = {
  name: string;
  list: string[];
  detail: string[];
  listWidths?: Record<string, number>;
};

export type WorkbenchFieldsSetting = {
  list: string[];
  detail: string[];
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

  // --- Named layouts ---
  const [activeViewName, setActiveViewName] = useState<string | null>(null);

  // --- Column state ---
  const [colWidths, setColWidths] = useState<Record<string, number>>({});

  // --- Field behaviors ---
  const [fieldBehaviors, setFieldBehaviors] = useState<Record<string, any>>({});
  const [detailRowSizes, setDetailRowSizes] = useState<Record<string, number>>({});

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  const modelParam = searchParams.get('model');

  const modelLabel = useMemo(() => {
    if (!selectedModel) return 'Select model';
    const p = selectedModel.split('.');
    return p[p.length - 1] || selectedModel;
  }, [selectedModel]);

  const visibleListFields = useMemo(() => {
    if (workbenchSetting?.list?.length) return workbenchSetting.list;
    // Fallback: ida + first few actual fields from the model (no id, uuid)
    const fallback = allFields.filter((f) => f !== 'id' && f !== 'uuid' && f !== 'version' && f !== 'is_deleted' && f !== 'is_archived' && f !== 'is_locked' && f !== 'security_level' && f !== 'search_vector').slice(0, 6);
    return fallback.length ? fallback : ['ida'];
  }, [workbenchSetting?.list, allFields]);

  const visibleDetailFields = useMemo(() =>
    workbenchSetting?.detail?.length ? workbenchSetting.detail : allFields,
  [workbenchSetting?.detail, allFields]);

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

  const handleSelectModel = useCallback((name: string) => {
    dbLog('handleSelectModel', { from: selectedModel, to: name });
    // Increment change counter — any in-flight fetch for old model will be discarded
    modelChangeRef.current += 1;
    // Clear ALL state from previous model in one batch
    setSelectedModel(name);
    setPage(0);
    setActiveSearch(''); setSearchTerm('');
    setSort(null);
    setSubsetMode('all');
    setSelectedRowIds(new Set());
    setActiveViewName(null);
    setColWidths({});
    setSelectedId(null);
    setSelectedRecord(null);
    setAllFields([]);
    setFieldBehaviors({});
    setWorkbenchSetting(null);
    setRecords([]);
    setTotalRecords(0);
    setRecordsLoading(false);
    setRecordsError(null);
    fetchingRef.current = false;
    // Update URL directly — no second effect needed
    const next = new URLSearchParams(searchParams);
    next.set('model', name);
    setSearchParams(next, { replace: true });
    previousModelParam.current = name;
  }, [searchParams, setSearchParams]);

  // Sync model FROM URL param (browser back/forward, external navigation, initial load)
  useEffect(() => {
    if (!modelNames.length) { setRecords([]); setSelectedId(null); setSelectedRecord(null); previousModelParam.current = modelParam; return; }
    // Only react to URL changes we didn't cause ourselves
    if (modelParam && modelParam !== previousModelParam.current && modelNames.includes(modelParam)) {
      previousModelParam.current = modelParam;
      if (selectedModel !== modelParam) {
        handleSelectModel(modelParam);
      }
      return;
    }
    previousModelParam.current = modelParam;
    // No model selected yet — pick first
    if (!selectedModel || !modelNames.includes(selectedModel)) {
      handleSelectModel(modelNames[0]);
    }
  }, [modelNames, modelParam, selectedModel, handleSelectModel]);

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
        settings.forEach((s: any) => { map[s.parent_model || s.model_name] = s.data; });
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
    if (fetchingRef.current) { dbLog.warn('fetchRecords:skip (already fetching)'); return; }
    fetchingRef.current = true;
    const fetchId = modelChangeRef.current; // snapshot — if model changes mid-fetch, discard results
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
      try {
        const wsRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'workbench_fields', limit: 1 }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const wsRec = (wsRes?.results || [])[0];
        ws = wsRec?.data || null;
      } catch { /* use null */ }
      setWorkbenchSetting(ws);
      dbLog('fetchRecords:workbenchSetting', { model: selectedModel, list: ws?.list?.slice(0, 8), detail: ws?.detail?.slice(0, 8), views: ws?.views?.length });

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'field_access' }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const faRec = (faRes?.results || [])[0];
        setFieldBehaviors(faRec?.data?.field_behaviors || {});
      } catch { setFieldBehaviors({}); }
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

  // Load detail
  useEffect(() => {
    if (!selectedModel || selectedId == null) return;
    (async () => {
      const d = await getRecord(selectedModel, selectedId) as { record?: unknown };
      setSelectedRecord(toRec(d?.record));
      setIsDirty(false);
    })();
  }, [selectedModel, selectedId]);

  // ---------------------------------------------------------------------------
  // Field operations
  // ---------------------------------------------------------------------------

  const updateField = useCallback((f: string, v: unknown) => { setSelectedRecord((p) => p ? { ...p, [f]: v } : p); setIsDirty(true); }, []);

  const persistSetting = useCallback(async (model: string, next: WorkbenchFieldsSetting) => {
    try {
      const existing = await getWorkbenchFieldsSetting(model);
      await saveWorkbenchFieldsSetting({ id: existing?.id, model_name: model, purpose: 'workbench_fields', data: next });
    } catch (e) { console.error('Save settings failed:', e); }
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
      setColWidths((p) => ({ ...p, [resizingRef.current!.field]: Math.max(40, resizingRef.current!.startW + ev.clientX - resizingRef.current!.startX) }));
    };
    const onUp = () => { resizingRef.current = null; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  }, [colWidths]);

  // ---------------------------------------------------------------------------
  // Layouts
  // ---------------------------------------------------------------------------

  const saveView = useCallback(async (name: string) => {
    if (!selectedModel || !name.trim()) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const views = [...(cur.views || [])];
    const idx = views.findIndex((v) => v.name === name.trim());
    const view: NamedView = { name: name.trim(), list: cur.list || [], detail: cur.detail || [], listWidths: { ...colWidths } };
    if (idx >= 0) views[idx] = view; else views.push(view);
    const next: WorkbenchFieldsSetting = { ...cur, views };
    setWorkbenchSetting(next); setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    setActiveViewName(name.trim());
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, colWidths, persistSetting]);

  const loadView = useCallback((v: NamedView) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    setWorkbenchSetting({ ...cur, list: v.list, detail: v.detail });
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: { ...cur, list: v.list, detail: v.detail } }));
    setColWidths(v.listWidths || {}); setActiveViewName(v.name);
  }, [selectedModel, workbenchSetting]);

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

  // Save record
  const handleSaveRecord = useCallback(async () => {
    if (!selectedModel || !selectedRecord) return;
    await saveRecord(selectedModel, { ...selectedRecord });
    setIsDirty(false); fetchRecords();
  }, [selectedModel, selectedRecord, fetchRecords]);

  // Delete record
  const handleDeleteRecord = useCallback(async () => {
    if (!selectedModel || !selectedId || !confirm(`Delete ${modelLabel} #${selectedId}?`)) return;
    await deleteRecord(selectedModel, selectedId);
    setRecords((p) => p.filter((r) => numId(r.id) !== selectedId));
    setSelectedRecord(null); setSelectedId(null);
  }, [selectedModel, selectedId, modelLabel]);

  // Update list fields (from field order dialog)
  const updateListLayout = useCallback(async (fields: string[]) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const next: WorkbenchFieldsSetting = { ...cur, list: fields };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, persistSetting]);

  // Update detail fields (from field order dialog)
  const updateDetailLayout = useCallback(async (fields: string[], sizes: Record<string, number>) => {
    if (!selectedModel) return;
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const next: WorkbenchFieldsSetting = { ...cur, detail: fields };
    setWorkbenchSetting(next);
    setWorkbenchSettingsMap((p) => ({ ...p, [selectedModel]: next }));
    setDetailRowSizes(sizes);
    await persistSetting(selectedModel, next);
  }, [selectedModel, workbenchSetting, persistSetting]);

  return {
    // Model
    modelNames, loadingModels, modelsError, selectedModel, modelLabel, modelParam,
    handleSelectModel,
    // Records
    records, recordsLoading, recordsError, totalRecords, page, setPage, totalPages,
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
    workbenchSetting, toggleField, bulkSetFields,
    // Layouts
    savedViews, activeViewName, saveView, loadView, deleteView,
    // Columns
    colWidths, setColWidths, handleColumnDrop, handleResizeStart,
    // Field behaviors
    fieldBehaviors, detailRowSizes, setDetailRowSizes,
    // CRUD
    updateField, handleSaveRecord, handleDeleteRecord,
    updateListLayout,
    updateDetailLayout,
    // Export
    exportCSV,
  };
}
