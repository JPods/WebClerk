/**
 * useListFieldConfig — adds DataBrowser-style field selection and ordering to any list page.
 *
 * Usage in a list page:
 *   const allColumns = useMemo(() => [...], []);  // your full column definitions
 *   const { visibleColumns, FieldConfigBar } = useListFieldConfig('customer', allColumns);
 *   // render FieldConfigBar above the table, pass visibleColumns to AdvancedDataTable
 *
 * Saves field visibility + order to the same workbench_fields Setting used by the DataBrowser,
 * so layouts are shared between dedicated pages and the DataBrowser.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { TableColumn } from 'react-data-table-component';
import {
  getWorkbenchFieldsSetting,
  saveWorkbenchFieldsSetting,
} from '@/api/wcapi';

// Stable key for a column — uses the `name` prop (header label)
function colKey(col: TableColumn<any>): string {
  return typeof col.name === 'string' ? col.name : String(col.id ?? '');
}

export function useListFieldConfig<T>(
  modelName: string,
  allColumns: TableColumn<T>[],
) {
  const [visibleKeys, setVisibleKeys] = useState<string[] | null>(null); // null = show all
  const [showPanel, setShowPanel] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Load saved config
  useEffect(() => {
    if (!modelName || loaded) return;
    (async () => {
      try {
        const setting = await getWorkbenchFieldsSetting(modelName);
        if (setting?.data?.list?.length) {
          setVisibleKeys(setting.data.list);
        }
      } catch { /* no saved config — show all */ }
      setLoaded(true);
    })();
  }, [modelName, loaded]);

  // All column keys in definition order
  const allKeys = useMemo(() => allColumns.map(colKey), [allColumns]);

  // Effective visible keys
  const effectiveKeys = visibleKeys ?? allKeys;

  // Filtered + ordered columns
  const visibleColumns = useMemo(() => {
    if (!visibleKeys) return allColumns;
    const colMap = new Map(allColumns.map((c) => [colKey(c), c]));
    return visibleKeys
      .map((k) => colMap.get(k))
      .filter((c): c is TableColumn<T> => !!c);
  }, [allColumns, visibleKeys]);

  // Persist
  const persist = useCallback(async (keys: string[]) => {
    if (!modelName) return;
    try {
      const existing = await getWorkbenchFieldsSetting(modelName);
      const data = existing?.data ?? { list: [], detail: [] };
      data.list = keys;
      await saveWorkbenchFieldsSetting({
        id: existing?.id,
        model_name: modelName,
        purpose: 'workbench_fields',
        data,
      });
    } catch (e) {
      console.error('Failed to save field config:', e);
    }
  }, [modelName]);

  const toggleField = useCallback((key: string) => {
    setVisibleKeys((prev) => {
      const current = prev ?? allKeys;
      const next = current.includes(key)
        ? current.filter((k) => k !== key)
        : [...current, key];
      persist(next);
      return next;
    });
  }, [allKeys, persist]);

  const setAll = useCallback(() => {
    setVisibleKeys(allKeys);
    persist(allKeys);
  }, [allKeys, persist]);

  const clearAll = useCallback(() => {
    const minimal = allKeys.slice(0, 1); // keep at least one
    setVisibleKeys(minimal);
    persist(minimal);
  }, [allKeys, persist]);

  const moveField = useCallback((key: string, direction: 'up' | 'down') => {
    setVisibleKeys((prev) => {
      const current = [...(prev ?? allKeys)];
      const idx = current.indexOf(key);
      if (idx < 0) return current;
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= current.length) return current;
      [current[idx], current[target]] = [current[target], current[idx]];
      persist(current);
      return current;
    });
  }, [allKeys, persist]);

  // Toggle panel visibility
  const toggle = useCallback(() => setShowPanel((p) => !p), []);

  return {
    visibleColumns,
    showPanel,
    togglePanel: toggle,
    effectiveKeys,
    allKeys,
    toggleField,
    setAll,
    clearAll,
    moveField,
  };
}
