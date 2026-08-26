/**
 * useListFieldConfig — unified column configuration with three-tier inheritance.
 *
 * Resolution chain (highest priority wins):
 *   1. localStorage (user's personal override)
 *   2. Report config.layout.list.default (context-specific override)
 *   3. Setting wc:model config.layout.list.default (system-wide default)
 *   4. Hardcoded column definitions (fallback)
 *
 * When a user changes columns, it saves to localStorage first.
 * "Reset to default" clears localStorage, falling back to Report or Setting.
 * Admin "Save to Setting" persists to the wc:model Setting for all users.
 *
 * Usage:
 *   const columns = useMemo(() => [...], []);
 *   const fc = useListFieldConfig('customer', columns);
 *   // or with report context:
 *   const fc = useListFieldConfig('panel:order:contacts', columns, { reportId: 42 });
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecords } from '@/api/wcapi';

/** Column shape compatible with legacy TableColumn */
type TableColumn<T = any> = {
  id?: string | number;
  name?: string | React.ReactNode;
  selector?: ((row: T, index?: number) => any) | string;
  cell?: (row: T, index: number, column: any, id: any) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  [key: string]: any;
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Column spec as stored in layout.list.default.columns */
export interface ListColumnSpec {
  field: string;
  label?: string;
  width?: number;
  format?: string;
  align?: string;
  visible?: boolean;
}

export interface SavedLayout {
  name: string;
  list: string[];
  detail: string[];
  listWidths?: Record<string, number>;
}

interface ListLayoutDefault {
  columns?: ListColumnSpec[];
  form?: string;
  detail?: string;
  views?: SavedLayout[];
}

interface UseListFieldConfigOptions {
  /** Report ID for context-specific column override */
  reportId?: number;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const LS_PREFIX = 'wc:cols:';

function loadLocalStorage(storageKey: string): { keys?: string[]; widths?: Record<string, number> } | null {
  try {
    const raw = localStorage.getItem(LS_PREFIX + storageKey);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
}

function saveLocalStorage(storageKey: string, keys: string[], widths: Record<string, number>) {
  try {
    localStorage.setItem(LS_PREFIX + storageKey, JSON.stringify({ keys, widths }));
  } catch { /* quota exceeded */ }
}

function clearLocalStorage(storageKey: string) {
  try { localStorage.removeItem(LS_PREFIX + storageKey); } catch {}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function colKey(col: TableColumn<any>): string {
  return typeof col.name === 'string' ? col.name : String(col.id ?? '');
}

/** Extract model name from storageKey for Setting lookup.
 *  "panel:order:contacts" → "order"
 *  "customer" → "customer"
 */
function extractModelName(storageKey: string): string {
  const parts = storageKey.split(':');
  if (parts.length >= 2 && parts[0] === 'panel') return parts[1];
  return parts[0];
}

/** Parse a ListLayoutDefault into keys + widths */
function parseLayout(layout: ListLayoutDefault | undefined): { keys: string[]; widths: Record<string, number> } | null {
  if (!layout?.columns?.length) return null;
  const visibleCols = layout.columns.filter(c => c.visible !== false);
  const keys = visibleCols.map(c => c.field);
  const widths: Record<string, number> = {};
  for (const c of layout.columns) {
    if (c.width) widths[c.field] = c.width;
  }
  return { keys, widths };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useListFieldConfig<T>(
  storageKey: string,
  allColumns: TableColumn<T>[],
  options?: UseListFieldConfigOptions,
) {
  const [visibleKeys, setVisibleKeys] = useState<string[] | null>(null);
  const [colWidths, setColWidths] = useState<Record<string, number>>({});
  const [savedLayouts, setSavedLayouts] = useState<SavedLayout[]>([]);
  const [activeLayoutName, setActiveLayoutName] = useState<string | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [fieldBehaviors, setFieldBehaviors] = useState<Record<string, any>>({});
  const [settingId, setSettingId] = useState<number | undefined>();
  const [configSource, setConfigSource] = useState<'local' | 'report' | 'setting' | 'default'>('default');

  const modelName = extractModelName(storageKey);

  // Load config with three-tier inheritance
  useEffect(() => {
    if (!storageKey || loaded) return;
    (async () => {
      let resolved = false;

      // ── Tier 1: localStorage (user's personal override) ──
      const local = loadLocalStorage(storageKey);
      if (local?.keys?.length) {
        setVisibleKeys(local.keys);
        if (local.widths) setColWidths(local.widths);
        setConfigSource('local');
        resolved = true;
      }

      // ── Tier 2: Report config (context-specific override) ──
      if (!resolved && options?.reportId) {
        try {
          const res = await getRecords('report', { id: options.reportId, limit: 1 }) as any;
          const report = res?.results?.[0] ?? res?.records?.[0];
          if (report) {
            const layout = report?.config?.layout?.list?.default as ListLayoutDefault | undefined;
            const parsed = parseLayout(layout);
            if (parsed) {
              setVisibleKeys(parsed.keys);
              setColWidths(parsed.widths);
              setConfigSource('report');
              resolved = true;
            }
            if (layout?.views) setSavedLayouts(layout.views);
          }
        } catch { /* no report config */ }
      }

      // ── Tier 3: Setting wc:model (system-wide default) ──
      try {
        const res = await getRecords('setting', {
          parent_model: modelName,
          purpose: 'wc:model',
          limit: 1,
        }) as any;
        const setting = res?.results?.[0] ?? res?.records?.[0];
        if (setting) {
          setSettingId(setting.id);
          if (!resolved) {
            const layout = setting?.config?.layout?.list?.default as ListLayoutDefault | undefined;
            const parsed = parseLayout(layout);
            if (parsed) {
              setVisibleKeys(parsed.keys);
              setColWidths(parsed.widths);
              setConfigSource('setting');
              resolved = true;
            }
            if (layout?.views) setSavedLayouts(layout.views);
          }
        }
      } catch { /* no setting */ }

      // ── Tier 4: hardcoded defaults (allColumns as-is) ──
      // visibleKeys stays null → effectiveKeys falls back to allKeys

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: modelName, purpose: 'wc:field_access' }) as any;
        const faRec = (faRes?.results || [])[0];
        if (faRec?.config?.field_behaviors) setFieldBehaviors(faRec.config.field_behaviors);
      } catch { /* no behaviors */ }

      setLoaded(true);
    })();
  }, [storageKey, modelName, loaded, options?.reportId]);

  // All column keys
  const allKeys = useMemo(() => allColumns.map(colKey), [allColumns]);
  const effectiveKeys = visibleKeys ?? allKeys;

  // Filtered + ordered columns for AdvancedDataTable compatibility
  const visibleColumns = useMemo(() => {
    if (!visibleKeys) return allColumns;
    const colMap = new Map(allColumns.map((c) => [colKey(c), c]));
    return visibleKeys
      .map((k) => colMap.get(k))
      .filter((c): c is TableColumn<T> => !!c);
  }, [allColumns, visibleKeys]);

  // ── Persist to localStorage (user-level) ──
  const persistLocal = useCallback((keys: string[], widths: Record<string, number>) => {
    saveLocalStorage(storageKey, keys, widths);
    setConfigSource('local');
  }, [storageKey]);

  // ── Persist to Setting (admin-level — system-wide default) ──
  const persistToSetting = useCallback(async (
    keys?: string[],
    widths?: Record<string, number>,
    layouts?: SavedLayout[],
  ) => {
    if (!modelName || !settingId) return;
    try {
      const res = await getRecords('setting', {
        parent_model: modelName,
        purpose: 'wc:model',
        limit: 1,
      }) as any;
      const setting = res?.results?.[0] ?? res?.records?.[0];
      if (!setting) return;

      const config = { ...setting.config };
      const layout = { ...config.layout };
      const list = { ...layout.list };
      const listDefault = { ...(list.default || {}) };

      if (keys || widths) {
        const existingCols: ListColumnSpec[] = listDefault.columns || [];
        const colMap = new Map(existingCols.map(c => [c.field, c]));
        if (keys) {
          const ordered: ListColumnSpec[] = keys.map(k =>
            colMap.get(k) ?? { field: k, label: k, visible: true }
          );
          for (const c of existingCols) {
            if (!keys.includes(c.field)) {
              ordered.push({ ...c, visible: false });
            }
          }
          listDefault.columns = ordered;
        }
        if (widths) {
          for (const col of (listDefault.columns || [])) {
            if (widths[col.field] !== undefined) {
              col.width = widths[col.field];
            }
          }
        }
      }
      if (layouts) listDefault.views = layouts;

      list.default = listDefault;
      layout.list = list;
      config.layout = layout;

      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord('setting', { ...setting, config });
    } catch (e) {
      console.error('Failed to save list config to Setting:', e);
    }
  }, [modelName, settingId]);

  // Update list fields — saves to localStorage
  const updateListFields = useCallback((keys: string[]) => {
    setVisibleKeys(keys);
    persistLocal(keys, colWidths);
  }, [persistLocal, colWidths]);

  // Update widths
  const updateWidths = useCallback((widths: Record<string, number>) => {
    setColWidths(widths);
    if (visibleKeys) persistLocal(visibleKeys, widths);
  }, [persistLocal, visibleKeys]);

  // Reset to inherited default (clear localStorage, fall back to Report or Setting)
  const resetToDefault = useCallback(() => {
    clearLocalStorage(storageKey);
    setVisibleKeys(null);
    setColWidths({});
    setConfigSource('default');
    setLoaded(false); // triggers re-load from Report/Setting
  }, [storageKey]);

  // Save current config to Setting (admin action — becomes default for all users)
  const saveToSetting = useCallback(() => {
    persistToSetting(visibleKeys ?? allKeys, colWidths, savedLayouts);
  }, [persistToSetting, visibleKeys, allKeys, colWidths, savedLayouts]);

  // Save layout
  const saveLayout = useCallback((name: string) => {
    const layout: SavedLayout = {
      name,
      list: visibleKeys ?? allKeys,
      detail: [],
      listWidths: colWidths,
    };
    const updated = [...savedLayouts.filter((l) => l.name !== name), layout];
    setSavedLayouts(updated);
    setActiveLayoutName(name);
    persistToSetting(undefined, undefined, updated);
  }, [visibleKeys, allKeys, colWidths, savedLayouts, persistToSetting]);

  // Load layout
  const loadLayout = useCallback((layout: SavedLayout) => {
    setVisibleKeys(layout.list);
    if (layout.listWidths) setColWidths(layout.listWidths);
    setActiveLayoutName(layout.name);
    persistLocal(layout.list, layout.listWidths || {});
  }, [persistLocal]);

  // Delete layout
  const deleteLayout = useCallback((name: string) => {
    if (!confirm(`Delete layout "${name}"?`)) return;
    const updated = savedLayouts.filter((l) => l.name !== name);
    setSavedLayouts(updated);
    if (activeLayoutName === name) setActiveLayoutName(null);
    persistToSetting(undefined, undefined, updated);
  }, [savedLayouts, activeLayoutName, persistToSetting]);

  // Toggle dialog
  const toggleDialog = useCallback(() => setShowDialog((p) => !p), []);

  // FieldOrderDialog props
  const fieldOrderDialogProps = useMemo(() => ({
    open: showDialog,
    mode: 'list' as const,
    allFields: allKeys,
    visibleFields: effectiveKeys,
    fieldBehaviors,
    colWidths,
    savedLayouts,
    activeLayoutName,
    onApply: (fields: string[], _rowSizes: Record<string, number>, newWidths: Record<string, number>) => {
      updateListFields(fields);
      updateWidths(newWidths);
    },
    onSaveLayout: saveLayout,
    onLoadLayout: loadLayout,
    onDeleteLayout: deleteLayout,
    onClose: () => setShowDialog(false),
  }), [showDialog, allKeys, effectiveKeys, fieldBehaviors, colWidths, savedLayouts, activeLayoutName, updateListFields, updateWidths, saveLayout, loadLayout, deleteLayout]);

  // DataGrid props
  const dataGridColumnProps = useMemo(() => ({
    columns: effectiveKeys,
    colWidths,
  }), [effectiveKeys, colWidths]);

  return {
    // For AdvancedDataTable
    visibleColumns,
    // For DataGrid
    dataGridColumnProps,
    // Shared
    allKeys,
    effectiveKeys,
    colWidths,
    fieldBehaviors,
    savedLayouts,
    activeLayoutName,
    configSource,
    // Actions
    updateListFields,
    updateWidths,
    saveLayout,
    loadLayout,
    deleteLayout,
    resetToDefault,
    saveToSetting,
    // Dialog
    showDialog,
    toggleDialog,
    fieldOrderDialogProps,
  };
}
