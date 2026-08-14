/**
 * useDataBrowser — all state and data management for the DataBrowser.
 *
 * Extracts: model selection, records fetch, search, sort, pagination,
 * field config, named layouts, subset filtering, CRUD, field behaviors.
 *
 * Reusable — any page that needs a model browser can call this hook.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams, useParams, useNavigate } from 'react-router-dom';
import { useWindowPath } from '@/context/WindowPathContext';
import { useWindowManagerSafe } from '@/context/WindowManagerContext';
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

export type FieldGroup = {
  key: string;
  label: string;
  fields: string[];
};

export type WorkbenchFieldsSetting = {
  list: (string | FieldSpec)[];
  detail: (string | FieldSpec)[];
  related?: string[];   // FK model names shown as panels in detail view
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

export function useDataBrowser(isAuthenticated: boolean, defaultModel?: string, extraFilters?: Record<string, unknown>) {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeParams = useParams<{ model?: string }>();
  const navigate = useNavigate();
  const previousModelParam = useRef<string | null>(null);

  // Determine if this DataBrowser instance is in the active window.
  // Inactive windows should not react to URL changes or fire API calls.
  const windowPath = useWindowPath();
  const wmCtx = useWindowManagerSafe();
  const activePath = wmCtx?.activePath ?? null;
  const isActiveWindow = !windowPath || !activePath || windowPath.split('?')[0] === activePath.split('?')[0];

  // Capture URL filter params on mount (e.g. dt_created__gte from dashboard links)
  const urlFiltersRef = useRef<Record<string, string> | null>(null);
  if (urlFiltersRef.current === null) {
    const filters: Record<string, string> = {};
    const sp = new URLSearchParams(window.location.search);
    sp.forEach((v, k) => {
      if (k !== 'model' && k.includes('__')) filters[k] = v;
    });
    urlFiltersRef.current = filters;
  }

  // Stable key for extraFilters to avoid infinite re-fetch
  const extraFiltersKey = useMemo(() => extraFilters ? JSON.stringify(extraFilters) : '', [extraFilters]);

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

  // --- Field groups ---
  const [fieldGroups, setFieldGroups] = useState<FieldGroup[]>([]);
  const [defaultCollapsed, setDefaultCollapsed] = useState<string[]>([]);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, string[]>>({});

  /** Which groups are currently collapsed for this model */
  const currentCollapsed = useMemo(() => {
    if (!selectedModel) return defaultCollapsed;
    return collapsedGroups[selectedModel] ?? defaultCollapsed;
  }, [selectedModel, collapsedGroups, defaultCollapsed]);

  /** Toggle a field group's collapsed state; persist to wcui prefs */
  const toggleFieldGroup = useCallback((groupKey: string) => {
    if (!selectedModel) return;
    const cur = collapsedGroups[selectedModel] ?? [...defaultCollapsed];
    const next = cur.includes(groupKey) ? cur.filter(k => k !== groupKey) : [...cur, groupKey];
    setCollapsedGroups(prev => ({ ...prev, [selectedModel]: next }));
    // Persist — fire and forget
    import('@/utils/wcuiPrefs').then(({ setWcuiPref, getWcuiPref }) => {
      const all = getWcuiPref<Record<string, string[]>>('detail_collapsed', {});
      setWcuiPref('detail_collapsed', { ...all, [selectedModel]: next });
    });
  }, [selectedModel, collapsedGroups, defaultCollapsed]);

  // Load user's saved collapse state from wcui prefs on model change
  useEffect(() => {
    if (!selectedModel) return;
    if (collapsedGroups[selectedModel] !== undefined) return; // already loaded
    import('@/utils/wcuiPrefs').then(({ getWcuiPref }) => {
      const all = getWcuiPref<Record<string, string[]>>('detail_collapsed', {});
      if (all[selectedModel]) {
        setCollapsedGroups(prev => ({ ...prev, [selectedModel]: all[selectedModel] }));
      }
    });
  }, [selectedModel]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  // Route param (/:model) takes priority, then search param (?model=X), then pathname
  // Exclude known route paths that are NOT model names (e.g. /databrowser, /admin-wb, /db)
  const ROUTE_PATHS = new Set(['databrowser', 'admin-wb', 'db', 'dashboard', 'kanban', 'gantt', 'commerce', 'accounting', 'whitelist', 'json-viewer', 'json-tree', 'help', 'profile', 'training', 'docs', 'inventory-dashboard', 'inventory-adjust', 'cycle-count', 'administration', 'alice-dashboard', 'test-dashboard', 'report-designer', 'model-workbench']);
  const rawPathname = window.location.pathname.split('/').filter(Boolean)[0] || '';
  const pathnameModel = ROUTE_PATHS.has(rawPathname) ? '' : rawPathname;
  const modelParam = routeParams.model || searchParams.get('model') || pathnameModel || defaultModel || '';

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
    // On a /:model route, navigate to /<newModel> (stays in same window).
    // On /databrowser, use search params to stay in the same window/component instance.
    if (routeParams.model) {
      navigate(`/${name}`, { replace: true });
    } else {
      const next = new URLSearchParams(searchParams);
      next.set('model', name);
      setSearchParams(next, { replace: true });
    }
    previousModelParam.current = name;
  }, [searchParams, setSearchParams, routeParams.model, navigate]);

  // Sync model FROM URL param (browser back/forward, external navigation, initial load ONLY)
  // This effect should NOT run when handleSelectModel changes the URL — previousModelParam guards that
  // Only the ACTIVE window reacts to URL changes — inactive windows keep their last model
  useEffect(() => {
    if (!isActiveWindow) return;
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
  }, [modelNames, modelParam, selectedModel, isActiveWindow]); // include selectedModel to detect stale state

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
        settings.forEach((s: any) => { map[s.parent_model || s.model_name] = s.config?.db || s.config; });
        setWorkbenchSettingsMap(map);
      } catch (e) { setModelsError(errMsg(e, 'Failed to load models')); }
      finally { setLoadingModels(false); }
    })();
  }, [isAuthenticated]);

  // ---------------------------------------------------------------------------
  // Fetch records
  // ---------------------------------------------------------------------------

  const fetchRecords = useCallback(async () => {
    if (!isActiveWindow) return; // inactive windows don't fetch
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
      if (activeSearch.trim().length >= 3) params.keyword = activeSearch.trim();
      if (sort) params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field;
      // Apply URL filter params (e.g. dt_created__gte from dashboard drill-down links)
      const urlFilters = urlFiltersRef.current;
      if (urlFilters) {
        for (const [k, v] of Object.entries(urlFilters)) {
          if (!params[k]) params[k] = v;
        }
      }
      // Apply extra filters (e.g. date range from header)
      if (extraFilters) {
        for (const [k, v] of Object.entries(extraFilters)) {
          if (v !== undefined && v !== null && v !== '') params[k] = v;
        }
      }

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
        const wsRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'wc:workbench_fields', limit: 1 }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const wsRec = (wsRes?.results || [])[0];
        ws = wsRec?.config?.db || wsRec?.config || null;
        wsId = wsRec?.id ?? null;
      } catch { /* use null */ }
      setWorkbenchSetting(ws);
      setWorkbenchSettingId(wsId);
      if (wsId && selectedModel) workbenchSettingIdMap.current[selectedModel] = wsId;
      dbLog('fetchRecords:workbenchSetting', { model: selectedModel, settingId: wsId, list: ws?.list?.slice(0, 8), detail: ws?.detail?.slice(0, 8), views: ws?.views?.length });

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: selectedModel, purpose: 'wc:field_access' }) as any;
        if (modelChangeRef.current !== fetchId) return;
        const faRec = (faRes?.results || [])[0];
        const behaviors = faRec?.config?.field_behaviors || {};

        // Dynamic assigned_to select for action model — three-tier fallback
        if (selectedModel === 'action' && behaviors.assigned_to) {
          const settingAssignTo = faRec?.prefs?.assigned_to;
          let assignOptions: { label: string; value: string }[] = [];

          // Tier 1: try active project — refs.links (full roster) then prefs.assign_to (curated)
          try {
            const projRes = await getRecords('project', {
              status__in: 'open,in_progress',
              order_by: '-dt_modified',
              limit: 1,
            }) as any;
            const proj = (projRes?.results || [])[0];

            // Tier 1a: flatten refs.links — vendor, customer, contact, manufacturer
            const links = proj?.refs?.links || {};
            const roster: { id?: number; name?: string; role?: string }[] = [];
            for (const linkType of ['contact', 'vendor', 'customer', 'manufacturer']) {
              const arr = links[linkType];
              if (Array.isArray(arr)) {
                arr.forEach((c: any) => {
                  if (c.id || c.name) roster.push({ id: c.id, name: c.name || c.label, role: linkType });
                });
              }
            }
            if (roster.length > 0) {
              // Deduplicate by id
              const seen = new Set<number>();
              assignOptions = roster.filter(r => { if (!r.id || seen.has(r.id)) return false; seen.add(r.id); return true; })
                .map(r => ({
                  label: `${r.name}${r.role && r.role !== 'contact' ? ` (${r.role})` : ''}`,
                  value: JSON.stringify({ id: r.id, name: r.name, role: r.role }),
                }));
            }

            // Tier 1b: curated prefs.assign_to overrides refs if present
            const projAssignTo = proj?.prefs?.assigned_to;
            if (Array.isArray(projAssignTo) && projAssignTo.length > 0) {
              assignOptions = projAssignTo.map((p: any) => ({
                label: p.name || p.label || `Contact ${p.id}`,
                value: JSON.stringify({ id: p.id, name: p.name || p.label, role: p.role }),
              }));
            }
          } catch { /* project fetch failed — fall through */ }

          // Tier 2: setting.prefs.assign_to
          if (assignOptions.length === 0 && Array.isArray(settingAssignTo) && settingAssignTo.length > 0) {
            assignOptions = settingAssignTo.map((p: any) => ({
              label: p.name || p.label || `Contact ${p.id}`,
              value: JSON.stringify({ id: p.id, name: p.name || p.label }),
            }));
          }

          // Tier 3: hardcoded crew seed
          if (assignOptions.length === 0) {
            assignOptions = [
              { label: 'Bill James', value: JSON.stringify({ id: 8, name: 'Bill James' }) },
              { label: 'Claude Code', value: JSON.stringify({ id: 10627, name: 'Claude Code' }) },
              { label: 'Allie', value: JSON.stringify({ name: 'Allie' }) },
              { label: 'Alice', value: JSON.stringify({ name: 'Alice' }) },
              { label: 'Noelle', value: JSON.stringify({ name: 'Noelle' }) },
              { label: 'Nora', value: JSON.stringify({ name: 'Nora' }) },
            ];
          }

          behaviors.assigned_to = {
            ...behaviors.assigned_to,
            type: 'select',
            source: 'inline',
            options: assignOptions,
          };
        }

        setFieldBehaviors(behaviors);
        setFieldDefaults(faRec?.prefs?.defaults || {});
        setFieldGroups(faRec?.config?.field_groups || []);
        setDefaultCollapsed(faRec?.config?.default_collapsed || []);
      } catch { setFieldBehaviors({}); setFieldDefaults({}); setFieldGroups([]); setDefaultCollapsed([]); }
    } catch (e) {
      if (modelChangeRef.current !== fetchId) return; // don't show error for stale fetch
      const msg = errMsg(e, 'Failed to load records');
      setRecordsError(msg);
      dbLog.error('fetchRecords:failed', { model: selectedModel, error: msg });
    }
    finally { setRecordsLoading(false); fetchingRef.current = false; }
  }, [selectedModel, modelNames, page, activeSearch, sort, isActiveWindow, extraFiltersKey]);
  // NOTE: workbenchSettingsMap intentionally excluded — it changes when layouts are saved,
  // which would cause infinite re-fetch. We read it inside fetchRecords via closure.

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  // Auto-select record from sessionStorage (set by MacTopBar double-click, spawn links, etc.)
  const autoSelectDone = useRef(false);
  useEffect(() => {
    if (autoSelectDone.current || !records.length || !isActiveWindow) return;
    const stored = sessionStorage.getItem('db_auto_select');
    if (stored) {
      sessionStorage.removeItem('db_auto_select');
      const id = parseInt(stored, 10);
      if (!isNaN(id)) { setSelectedId(id); autoSelectDone.current = true; }
    }
  }, [records, isActiveWindow]);

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
          // Surgical update: write to config.db.* path
          const ops: Record<string, any> = {
            id: settingId,
            'config.db.list': { mode: 'update', value: next.list || [] },
            'config.db.detail': { mode: 'update', value: next.detail || [] },
            'config.db.related': { mode: 'update', value: next.related || [] },
          };
          // Upsert each named view individually
          for (const view of (next.views || [])) {
            if (view.name) {
              ops['config.db.views'] = { mode: 'upsert', key: 'name', value: view };
            }
          }
          await saveRecord('setting', ops);
        } else {
          const result = await saveRecord('setting', {
            name: `workbench_fields:${model}`,
            parent_model: model,
            purpose: 'wc:workbench_fields',
            config: { db: next },
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

  // Column resize — with width tooltip
  const resizingRef = useRef<{ field: string; startX: number; startW: number } | null>(null);
  const resizeTooltipRef = useRef<HTMLDivElement | null>(null);

  const _showResizeTooltip = (x: number, y: number, width: number, field?: string) => {
    if (!resizeTooltipRef.current) {
      const tip = document.createElement('div');
      tip.style.cssText = 'position:fixed;padding:2px 6px;background:#1e40af;color:#fff;font-size:11px;border-radius:3px;pointer-events:none;z-index:9999;font-family:monospace;white-space:nowrap;';
      document.body.appendChild(tip);
      resizeTooltipRef.current = tip;
    }
    resizeTooltipRef.current.textContent = `${width}px`;
    resizeTooltipRef.current.style.left = `${x + 12}px`;
    resizeTooltipRef.current.style.top = `${y - 8}px`;
  };

  const _hideResizeTooltip = () => {
    if (resizeTooltipRef.current) {
      resizeTooltipRef.current.remove();
      resizeTooltipRef.current = null;
    }
  };

  // Click on width badge to type a value directly
  const handleWidthClick = useCallback((field: string, anchor: HTMLElement) => {
    const currentW = colWidths[field] || 120;
    const rect = anchor.getBoundingClientRect();
    const input = document.createElement('input');
    input.type = 'number';
    input.min = '3';
    input.max = '800';
    input.value = String(currentW);
    input.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.bottom + 2}px;width:60px;padding:2px 4px;font-size:11px;font-family:monospace;text-align:center;border:1px solid #1e40af;border-radius:3px;background:#1a1a2e;color:#fff;z-index:9999;outline:none;`;
    document.body.appendChild(input);
    input.focus();
    input.select();
    const commit = () => {
      const v = Math.max(3, parseInt(input.value) || currentW);
      setColWidths((p) => ({ ...p, [field]: v }));
      // Local only — user must click Save to persist
      input.remove();
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') commit();
      if (e.key === 'Escape') input.remove();
    });
    input.addEventListener('blur', commit);
  }, [colWidths, selectedModel, workbenchSetting, persistSetting]);

  const handleResizeStart = useCallback((field: string, e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    // Use the actual rendered width of the th element, not the stored value
    const th = (e.target as HTMLElement).closest('th');
    const renderedW = th ? th.getBoundingClientRect().width : (colWidths[field] || 120);
    resizingRef.current = { field, startX: e.clientX, startW: Math.round(renderedW) };
    const onMove = (ev: MouseEvent) => {
      if (!resizingRef.current) return;
      const newW = Math.max(5, resizingRef.current!.startW + ev.clientX - resizingRef.current!.startX);
      setColWidths((p) => ({ ...p, [resizingRef.current!.field]: newW }));
      _showResizeTooltip(ev.clientX, ev.clientY, newW);
    };
    const onUp = () => {
      resizingRef.current = null;
      _hideResizeTooltip();
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      // Width change is local only — user must click Save to persist
    };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  }, [colWidths, selectedModel, workbenchSetting, persistSetting]);

  // ---------------------------------------------------------------------------
  // Layouts
  // ---------------------------------------------------------------------------

  const saveView = useCallback(async (name: string, fields?: (string | FieldSpec)[], mode?: 'list' | 'detail', dialogWidths?: Record<string, number>) => {
    if (!selectedModel || !name.trim()) return;
    if (PROTECTED_VIEWS.includes(name.trim().toLowerCase())) {
      alert(`"${name}" is a system layout and cannot be overwritten.`);
      return;
    }
    // Merge dialog widths (authoritative) with existing colWidths (fallback)
    const effectiveWidths = { ...colWidths, ...(dialogWidths || {}) };
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const views = [...(cur.views || [])];
    const idx = views.findIndex((v) => v.name === name.trim());
    // Convert fields to FieldSpec objects, merge with effective widths
    const specs = fields ? toFieldSpecs(fields).map(s => ({
      ...s,
      width: s.width || effectiveWidths[s.field] || undefined,
    })) : undefined;
    // Only update the side (list or detail) that changed — preserve the other
    const listSpecs = (mode === 'list' && specs) ? specs : cur.list || [];
    const detailSpecs = (mode === 'detail' && specs) ? specs : cur.detail || [];
    const view: NamedView = { name: name.trim(), list: listSpecs, detail: detailSpecs, listWidths: effectiveWidths };
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
      // Re-fetch detail to get updated version (prevents 412 on next save)
      if (selectedId != null) {
        const d = await getRecord(selectedModel, selectedId) as { record?: unknown };
        setSelectedRecord(toRec(d?.record));
      }
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
  const PROTECTED_VIEWS = ['alice_guess', 'alphabetical', 'alpha', 'best_guess', 'flat'];

  // Update list fields — persists to data.list (survives reload) but does NOT touch named views.
  // User must explicitly Save/Save As to commit to a named view.
  const updateListLayout = useCallback(async (fields: (string | FieldSpec)[], dialogWidths?: Record<string, number>) => {
    if (!selectedModel) return;
    const effectiveWidths = { ...colWidths, ...(dialogWidths || {}) };
    const cur = workbenchSetting ?? { list: [], detail: [] };
    const specs = toFieldSpecs(fields).map(s => ({
      ...s, width: s.width || effectiveWidths[s.field] || undefined,
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
    // Related panels
    relatedModels: workbenchSetting?.related || [],
    setRelatedModels: async (models: string[]) => {
      if (!selectedModel) return;
      const cur = workbenchSetting ?? { list: [], detail: [] };
      const next = { ...cur, related: models };
      setWorkbenchSetting(next);
      await persistSetting(selectedModel, next);
    },
    // Columns
    colWidths, setColWidths, handleColumnDrop, handleResizeStart, handleWidthClick,
    // Field behaviors
    fieldBehaviors, fieldDefaults, detailRowSizes, setDetailRowSizes,
    // Field groups
    fieldGroups, currentCollapsed, toggleFieldGroup,
    // CRUD
    updateField, handleSaveRecord, handleDeleteRecord, validationErrors,
    updateListLayout,
    updateDetailLayout,
    // Export
    exportCSV,
  };
}
