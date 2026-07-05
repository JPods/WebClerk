/**
 * useColumnContextMenu — provides right-click column management for any list page.
 *
 * Bridges the DataGrid context-menu props (allFields, namedViews, onDeleteColumn,
 * onAddColumn, onSaveLayout, onSaveLayoutAs, onLoadView) with a simple columns +
 * storageKey interface.
 *
 * Usage:
 *   const ctxMenu = useColumnContextMenu('order-list', userColumns, setVisibleColumns);
 *   <DataGrid {...ctxMenu} columns={visibleColumns} ... />
 */
import { useCallback, useMemo, useState, useEffect } from 'react';

type ColumnLike = {
  name?: string | React.ReactNode;
  id?: string | number;
  [key: string]: any;
};

interface NamedView {
  name: string;
  fields: string[];
}

interface UseColumnContextMenuResult {
  allFields: string[];
  namedViews: Array<{ name: string }>;
  onDeleteColumn: (field: string) => void;
  onAddColumn: (field: string, atIndex: number) => void;
  onSaveLayout: () => void;
  onSaveLayoutAs: () => void;
  onLoadView: (viewName: string) => void;
  /** The currently visible columns (filtered/reordered from allColumns) */
  visibleColumns: ColumnLike[];
}

function colKey(col: ColumnLike): string {
  if (typeof col.name === 'string') return col.name;
  return String(col.id ?? '');
}

export function useColumnContextMenu(
  storageKey: string,
  allColumns: ColumnLike[],
): UseColumnContextMenuResult {
  const viewsStorageKey = `${storageKey}:views`;
  const fieldsStorageKey = `${storageKey}:fields`;

  // All available field names from column definitions
  const allFields = useMemo(() => allColumns.map(colKey).filter(Boolean), [allColumns]);

  // Currently visible field keys (null = show all)
  const [visibleKeys, setVisibleKeys] = useState<string[] | null>(() => {
    try {
      const stored = localStorage.getItem(fieldsStorageKey);
      return stored ? JSON.parse(stored) : null;
    } catch { return null; }
  });

  // Named views
  const [views, setViews] = useState<NamedView[]>(() => {
    try {
      const stored = localStorage.getItem(viewsStorageKey);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  // Persist visible keys
  useEffect(() => {
    if (visibleKeys) {
      localStorage.setItem(fieldsStorageKey, JSON.stringify(visibleKeys));
    } else {
      localStorage.removeItem(fieldsStorageKey);
    }
  }, [visibleKeys, fieldsStorageKey]);

  // Persist views
  useEffect(() => {
    if (views.length) {
      localStorage.setItem(viewsStorageKey, JSON.stringify(views));
    } else {
      localStorage.removeItem(viewsStorageKey);
    }
  }, [views, viewsStorageKey]);

  const effectiveKeys = visibleKeys ?? allFields;

  const visibleColumns = useMemo(() => {
    if (!visibleKeys) return allColumns;
    const colMap = new Map(allColumns.map((c) => [colKey(c), c]));
    return visibleKeys
      .map((k) => colMap.get(k))
      .filter((c): c is ColumnLike => !!c);
  }, [allColumns, visibleKeys]);

  const onDeleteColumn = useCallback((field: string) => {
    setVisibleKeys((prev) => {
      const current = prev ?? allFields;
      return current.filter((k) => k !== field);
    });
  }, [allFields]);

  const onAddColumn = useCallback((field: string, atIndex: number) => {
    setVisibleKeys((prev) => {
      const current = [...(prev ?? allFields)];
      if (current.includes(field)) return current;
      current.splice(atIndex, 0, field);
      return current;
    });
  }, [allFields]);

  const onSaveLayout = useCallback(() => {
    // Save current arrangement as default (just persists current visibleKeys)
    const keys = visibleKeys ?? allFields;
    localStorage.setItem(fieldsStorageKey, JSON.stringify(keys));
  }, [visibleKeys, allFields, fieldsStorageKey]);

  const onSaveLayoutAs = useCallback(() => {
    const name = prompt('Layout name:');
    if (!name?.trim()) return;
    const trimmed = name.trim();
    const layout: NamedView = { name: trimmed, fields: visibleKeys ?? allFields };
    setViews((prev) => [...prev.filter((v) => v.name !== trimmed), layout]);
  }, [visibleKeys, allFields]);

  const onLoadView = useCallback((viewName: string) => {
    const view = views.find((v) => v.name === viewName);
    if (view) {
      setVisibleKeys(view.fields);
    }
  }, [views]);

  const namedViews = useMemo(() => views.map((v) => ({ name: v.name })), [views]);

  return {
    allFields,
    namedViews,
    onDeleteColumn,
    onAddColumn,
    onSaveLayout,
    onSaveLayoutAs,
    onLoadView,
    visibleColumns,
  };
}
