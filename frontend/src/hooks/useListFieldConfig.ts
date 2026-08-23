/**
 * useListFieldConfig — unified column configuration for any list page.
 *
 * Single source of truth: wc:model Setting → config.layout.list.default
 * Columns carry field, label, width, format, visible, align.
 *
 * Usage:
 *   const columns = useMemo(() => [...], []);
 *   const fc = useListFieldConfig('customer', columns);
 *   // Pass fc.visibleColumns to DataGrid
 *   // Use fc.fieldOrderDialogProps with FieldOrderDialog
 */
import { useCallback, useEffect, useMemo, useState } from 'react';

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
import {
  getRecords,
} from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Column spec as stored in wc:model layout.list.default.columns */
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function colKey(col: TableColumn<any>): string {
  return typeof col.name === 'string' ? col.name : String(col.id ?? '');
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useListFieldConfig<T>(
  modelName: string,
  allColumns: TableColumn<T>[],
) {
  const [visibleKeys, setVisibleKeys] = useState<string[] | null>(null);
  const [colWidths, setColWidths] = useState<Record<string, number>>({});
  const [savedLayouts, setSavedLayouts] = useState<SavedLayout[]>([]);
  const [activeLayoutName, setActiveLayoutName] = useState<string | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [fieldBehaviors, setFieldBehaviors] = useState<Record<string, any>>({});
  const [settingId, setSettingId] = useState<number | undefined>();

  // Load from wc:model Setting → config.layout.list.default
  useEffect(() => {
    if (!modelName || loaded) return;
    (async () => {
      try {
        const res = await getRecords('setting', {
          parent_model: modelName,
          purpose: 'wc:model',
          limit: 1,
        }) as any;
        const setting = res?.results?.[0] ?? res?.records?.[0];
        if (setting) {
          setSettingId(setting.id);
          const listLayout = setting?.config?.layout?.list?.default as ListLayoutDefault | undefined;
          if (listLayout?.columns?.length) {
            const visibleCols = listLayout.columns.filter((c: ListColumnSpec) => c.visible !== false);
            setVisibleKeys(visibleCols.map((c: ListColumnSpec) => c.field));
            const widths: Record<string, number> = {};
            for (const c of listLayout.columns) {
              if (c.width) widths[c.field] = c.width;
            }
            setColWidths(widths);
          }
          if (listLayout?.views) setSavedLayouts(listLayout.views);
        }
      } catch { /* no saved config */ }

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: modelName, purpose: 'wc:field_access' }) as any;
        const faRec = (faRes?.results || [])[0];
        if (faRec?.config?.field_behaviors) setFieldBehaviors(faRec.config.field_behaviors);
      } catch { /* no behaviors */ }

      setLoaded(true);
    })();
  }, [modelName, loaded]);

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

  // Persist to wc:model Setting → config.layout.list.default
  const persist = useCallback(async (
    keys?: string[],
    widths?: Record<string, number>,
    layouts?: SavedLayout[],
  ) => {
    if (!modelName || !settingId) return;
    try {
      // Re-fetch current wc:model Setting to avoid clobbering other layout sections
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

      // Update columns with new keys/widths
      if (keys || widths) {
        const existingCols: ListColumnSpec[] = listDefault.columns || [];
        const colMap = new Map(existingCols.map(c => [c.field, c]));
        if (keys) {
          // Reorder columns: keys first (visible), then remaining (hidden)
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

      // Save back via wcapi
      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord('setting', { ...setting, config });
    } catch (e) {
      console.error('Failed to save list config:', e);
    }
  }, [modelName, settingId]);

  // Update list fields
  const updateListFields = useCallback((keys: string[]) => {
    setVisibleKeys(keys);
    persist(keys);
  }, [persist]);

  // Update widths
  const updateWidths = useCallback((widths: Record<string, number>) => {
    setColWidths(widths);
  }, []);

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
    persist(undefined, undefined, updated);
  }, [visibleKeys, allKeys, colWidths, savedLayouts, persist]);

  // Load layout
  const loadLayout = useCallback((layout: SavedLayout) => {
    setVisibleKeys(layout.list);
    if (layout.listWidths) setColWidths(layout.listWidths);
    setActiveLayoutName(layout.name);
  }, []);

  // Delete layout
  const deleteLayout = useCallback((name: string) => {
    if (!confirm(`Delete layout "${name}"?`)) return;
    const updated = savedLayouts.filter((l) => l.name !== name);
    setSavedLayouts(updated);
    if (activeLayoutName === name) setActiveLayoutName(null);
    persist(undefined, undefined, updated);
  }, [savedLayouts, activeLayoutName, persist]);

  // Toggle dialog
  const toggleDialog = useCallback(() => setShowDialog((p) => !p), []);

  // FieldOrderDialog props — pass directly to the dialog
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

  // DataGrid props — pass directly to DataGrid
  const dataGridColumnProps = useMemo(() => ({
    columns: effectiveKeys,
    colWidths,
  }), [effectiveKeys, colWidths]);

  return {
    // For AdvancedDataTable (legacy compatibility)
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
    // Actions
    updateListFields,
    updateWidths,
    saveLayout,
    loadLayout,
    deleteLayout,
    // Dialog
    showDialog,
    toggleDialog,
    fieldOrderDialogProps,
  };
}
