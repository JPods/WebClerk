/**
 * useListFieldConfig — unified column configuration for any list page.
 *
 * Single hook that manages field selection, ordering, widths, and saved layouts.
 * Works with DataGrid columns.
 * Stores everything in workbench_fields Settings (same as DataBrowser).
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
  getWorkbenchFieldsSetting,
  saveWorkbenchFieldsSetting,
  getRecords,
} from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SavedLayout {
  name: string;
  list: string[];
  detail: string[];
  listWidths?: Record<string, number>;
}

interface WorkbenchData {
  list: string[];
  detail: string[];
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

  // Load saved config + field behaviors
  useEffect(() => {
    if (!modelName || loaded) return;
    (async () => {
      try {
        const setting = await getWorkbenchFieldsSetting(modelName);
        if (setting) {
          setSettingId(setting.id);
          const data = setting.config as WorkbenchData;
          if (data?.list?.length) setVisibleKeys(data.list);
          if (data?.views) setSavedLayouts(data.views);
          if ((setting as any).listWidths) setColWidths((setting as any).listWidths);
        }
      } catch { /* no saved config */ }

      // Load field behaviors
      try {
        const faRes = await getRecords('setting', { parent_model: modelName, purpose: 'field_access' }) as any;
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

  // Persist to Settings
  const persist = useCallback(async (
    keys?: string[],
    widths?: Record<string, number>,
    layouts?: SavedLayout[],
  ) => {
    if (!modelName) return;
    try {
      const existing = await getWorkbenchFieldsSetting(modelName);
      const data: WorkbenchData = existing?.data as WorkbenchData ?? { list: [], detail: [] };
      if (keys) data.list = keys;
      if (layouts) data.views = layouts;
      await saveWorkbenchFieldsSetting({
        id: existing?.id,
        model_name: modelName,
        purpose: 'workbench_fields',
        config: { ...data },
      });
    } catch (e) {
      console.error('Failed to save field config:', e);
    }
  }, [modelName]);

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
