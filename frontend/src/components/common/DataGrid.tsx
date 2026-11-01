/**
 * DataGrid — enhanced list table with all 10 features:
 *
 * 1. Column filters (per-column dropdown/search/range)
 * 2. Footer totals (sum/count for numeric columns)
 * 3. Inline cell edit (double-click → edit → Tab/Enter to save)
 * 4. Conditional row coloring (rules from Settings)
 * 5. Multi-sort (Ctrl-click for secondary sort)
 * 6. Pin first column (sticky left)
 * 7. Row grouping (group by field, collapsible)
 * 8. Bulk field update (select rows → set value)
 * 9. Print list
 * 10. Duplicate detection (highlight potential dupes)
 *
 * Replaces the inline table in DataBrowser.
 * Reusable in any page that needs a data table.
 */
import { EDIT_IN_LIST_HELP, LIST_HELP, useListGestures } from '@/hooks/useListGestures';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { parseFragments, matchesFragments } from '@/utils/searchFragments';
import { DbColumnsTable, type DbColumnDef } from '@/apps/common/components/panels/DbColumns';
import { cellAlign, cellTitle, fieldLabel, footerKind, formatCell, headerStyle, valueAt, type FooterKind } from '@/apps/common/components/panels/cellFormat';

// ---------------------------------------------------------------------------
// Universal dt formatter — stored GMT epoch ms, displayed local
// Rule: date-only fields → local date, time fields → local time, default → ISO local
// Field naming convention: dt_ prefix = datetime, date_ = date-only
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DataGridColumn {
  field: string;
  width?: number;
  pinned?: boolean;
}

export interface SortSpec {
  field: string;
  direction: 'asc' | 'desc';
  order: number; // 1-based sort priority
}

export interface RowColorRule {
  field: string;
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'empty' | 'notempty';
  value?: unknown;
  bg: string;
  text?: string;
  bold?: boolean;
}

export interface RichColumn {
  name: string;        // header label (used as key)
  field?: string;      // data field name (defaults to name)
  width?: string;      // e.g. "120px", "20%"
  cell?: (row: any) => React.ReactNode;  // custom cell renderer
  selector?: (row: any) => any;          // value accessor
  sortable?: boolean;
}

export interface DataGridProps {
  records?: any[];
  columns?: string[];                    // field names (simple mode)
  richColumns?: RichColumn[];            // rich column defs (optional, overrides simple)
  colWidths?: Record<string, number>;
  fieldSpecs?: Record<string, import('@/hooks/useDataBrowser').FieldSpec>;  // per-field formatting
  fieldBehaviors?: Record<string, any>;
  selectedId?: number | null;
  selectedRowIds?: Set<number>;
  sort?: { field: string; direction: 'asc' | 'desc' } | null;
  pinnedColumn?: string | null;
  colorRules?: RowColorRule[];
  groupByField?: string | null;
  onSelectRecord?: (id: number) => void;
  onToggleRow?: (id: number) => void;
  /** Given, a click only selects (the rows become this set) and a double-click opens the
   *  record (onSelectRecord): selecting groups never opens the frame (Bill, 2026-10-31).
   *  `moved` is the one row a plain click or arrow key went to — an open frame shows it;
   *  Shift and Cmd change only the selection. */
  onSelectRows?: (ids: Set<number>, moved?: number) => void;
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  onSort?: (field: string, multiSort?: boolean) => void;
  onColumnDrop?: (dragField: string, targetField: string) => void;
  onResizeStart?: (field: string, e: React.MouseEvent) => void;
  onWidthClick?: (field: string, anchor: HTMLElement) => void;
  /** Save one cell. A promise lets the cell show the result: green when saved, red with the reason. */
  onCellEdit?: (recordId: number, field: string, value: unknown) => void | Promise<void>;
  /** Edit-in-list (Bill, 2026-10-31): double-click edits a cell instead of opening the record;
   *  only plain values (text, numbers, choices) — not dates, links, or system-set fields. */
  editInList?: boolean;
  /** Edit-in-list: false for a field the list must not edit — one the save does not carry, or a
   *  copy of another record (a customer's attention is its contact's name). */
  fieldEditable?: (field: string) => boolean;
  onHeaderClick?: (field: string) => void;
  headerEditField?: string | null;
  headerEditValue?: string;
  onHeaderEditChange?: (value: string) => void;
  onHeaderEditApply?: () => void;
  onHeaderEditCancel?: () => void;
  numId?: (v: unknown) => number | null;
  theme?: any; // theme tokens
  fontSize?: number;

  // --- Column context menu (wc2 right-click pattern) ---
  allFields?: string[];                  // all available fields for "Add Column" submenu
  namedViews?: Array<{ name: string }>;  // named views for quick switching
  onDeleteColumn?: (field: string) => void;
  onAddColumn?: (field: string, atIndex: number) => void;
  onSaveLayout?: () => void;
  onSaveLayoutAs?: () => void;
  onLoadView?: (viewName: string) => void;

  // --- List-page convenience props (auto-managed state) ---
  /** Alias for records */
  data?: any[];
  /** Legacy TableColumn-style column defs; auto-mapped to richColumns */
  legacyColumns?: Array<{
    id?: string | number;
    name?: string | React.ReactNode;
    selector?: ((row: any, index?: number) => any) | string;
    cell?: (row: any, index: number, column: any, id: any) => React.ReactNode;
    sortable?: boolean;
    width?: string;
    sortField?: string;
    [key: string]: any;
  }>;
  /** Row click handler (receives full row object, not just id) */
  onRowClicked?: (row: any) => void;
  /** Row double-click handler */
  onRowDoubleClicked?: (row: any) => void;
  /** Option-double-click: the record in a browser window of its own (the WC List Standard). */
  onOpenWindow?: (row: any) => void;
  /** Cell click handler — receives event, field name, and row record */
  onCellClick?: (e: React.MouseEvent, field: string, row: any) => void;
  /** Row activate handler */
  onRowActivate?: (row: any) => void;
  /** Enable checkbox selection mode */
  enableSelection?: boolean;
  /** Called when selected rows change */
  onSelectionChange?: (rows: any[]) => void;
  /** Show loading spinner */
  loading?: boolean;
  /** External search term for client-side filtering */
  externalSearchTerm?: string;
  /** Callback for search term changes */
  onExternalSearchTermChange?: (s: string) => void;
  /** Message when no data */
  noDataMessage?: string;
  /** Hide the built-in header/toolbar */
  hideHeader?: boolean;
  /** Hide the built-in toolbar (Filter/Dupes/CSV/Print) — use when parent provides its own */
  hideToolbar?: boolean;
  /** Expose filter toggle to parent */
  onToggleFilters?: (show: boolean) => void;
  /** Expose dupes toggle to parent */
  onToggleDupes?: (show: boolean) => void;
  /** External control of filter visibility */
  externalShowFilters?: boolean;
  /** External control of dupes visibility */
  externalShowDupes?: boolean;

  // --- Line card / operational features (db.list with config) ---
  /** Custom footer bar content — rendered below the Σ row, above panels */
  footerBar?: React.ReactNode;
  /** Panel content — rendered below footer bar, show/hide controlled by parent */
  panelContent?: React.ReactNode;
  /** Locked columns — cannot be reordered or removed */
  lockedColumns?: Set<string>;
  /** Disable column reorder via drag */
  disableReorder?: boolean;
  /** Disable right-click "Add Column" */
  disableAddColumn?: boolean;

  // --- Props accepted for toolbar/sub-component passthrough ---
  title?: string;
  storageKey?: string;
  enableExport?: boolean;
  exportFileName?: string;
  searchPlaceholder?: string;
  customActions?: React.ReactNode;
  onAdd?: () => void;
  onEditSelected?: (row: any) => void;
  onDeleteSelected?: (rows: any[]) => void;
  onImportFile?: (f: File) => void;
  importAccept?: string;
  onPrint?: () => void;
  enableDatabaseSearch?: boolean;
  searchDatabase?: boolean;
  onSearchModeChange?: (searchDatabase: boolean) => void;
  onDatabaseSearch?: (terms: string[]) => Promise<void> | void;
  filters?: any;
  filtersOpen?: boolean;
  onFiltersOpenChange?: (open: boolean) => void;
  /** Called when column filters change — parent can use for server-side filtering */
  onFilterChange?: (filters: Record<string, string>) => void;
  onVisibleRowsChange?: (rows: any[]) => void;
  selectionMode?: string;
  enableSelectedOnlyFilter?: boolean;
  rowClickMode?: string;
  rowClickAllowedColumnNames?: string[];
  rowClickAllowedColumnIds?: Array<string | number>;
  rowKeyField?: string;
  ref?: any;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function matchesRule(record: any, rule: RowColorRule): boolean {
  const v = record[rule.field];
  switch (rule.operator) {
    case 'eq': return v === rule.value || String(v) === String(rule.value);
    case 'neq': return v !== rule.value && String(v) !== String(rule.value);
    case 'gt': return Number(v) > Number(rule.value);
    case 'lt': return Number(v) < Number(rule.value);
    case 'contains': return String(v ?? '').toLowerCase().includes(String(rule.value ?? '').toLowerCase());
    case 'empty': return v == null || v === '' || v === 0;
    case 'notempty': return v != null && v !== '' && v !== 0;
    default: return false;
  }
}

function detectDuplicates(records: any[], columns: string[]): Set<number> {
  // Check first 3 visible columns for identical values
  const checkFields = columns.slice(0, 3);
  const seen = new Map<string, number[]>();
  const dupeIds = new Set<number>();

  records.forEach((rec) => {
    const key = checkFields.map((f) => String(rec[f] ?? '')).join('|');
    if (!key || key === checkFields.map(() => '').join('|')) return;
    const existing = seen.get(key);
    if (existing) {
      existing.forEach((id) => dupeIds.add(id));
      if (rec.id) dupeIds.add(rec.id);
    } else {
      seen.set(key, rec.id ? [rec.id] : []);
    }
  });

  return dupeIds;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Helpers for legacy column mapping
// ---------------------------------------------------------------------------

function _getFieldName(col: any, idx: number): string {
  if (typeof col.id === 'string') return col.id;
  if (typeof col.id === 'number') return `col_${col.id}`;
  if (typeof col.name === 'string') return col.name;
  if (typeof col.sortField === 'string') return col.sortField;
  return `col_${idx}`;
}

function _numId(v: unknown): number | null {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') { const n = Number(v); return Number.isFinite(n) ? n : null; }
  return null;
}


export default function DataGrid(props: DataGridProps) {
  // --- Resolve convenience vs explicit props ---
  const inputData = props.records ?? props.data ?? [];
  const legacyCols = props.legacyColumns ?? (props.columns ? null : null);

  // Map legacy columns if provided (detected by presence of objects with 'name'+'selector' shape)
  // Also detect if props.columns is actually an array of legacy column objects
  const isLegacyColumnArray = useMemo(() => {
    const c = (props as any).columns;
    if (!Array.isArray(c) || c.length === 0) return false;
    return typeof c[0] === 'object' && c[0] !== null && ('name' in c[0] || 'selector' in c[0] || 'cell' in c[0]);
  }, [(props as any).columns]);

  const effectiveLegacyCols = legacyCols ?? (isLegacyColumnArray ? (props as any).columns : null);

  const mappedColumns = useMemo(() => {
    if (!effectiveLegacyCols) return null;
    const fieldNames: string[] = effectiveLegacyCols.map((c: any, i: number) => _getFieldName(c, i));
    const rich: RichColumn[] = effectiveLegacyCols.map((col: any, idx: number) => {
      const field = fieldNames[idx];
      const rc: RichColumn = {
        name: typeof col.name === 'string' ? col.name : field,
        field,
        width: col.width,
        sortable: col.sortable ?? false,
      };
      if (col.cell) {
        const cellFn = col.cell;
        rc.cell = (row: any) => cellFn(row, 0, col, row.id);
      }
      if (col.selector && typeof col.selector === 'function') {
        const sel = col.selector;
        rc.selector = (row: any) => sel(row);
      }
      return rc;
    });
    const widths: Record<string, number> = {};
    effectiveLegacyCols.forEach((col: any, idx: number) => {
      const field = fieldNames[idx];
      if (col.width) {
        const px = parseInt(col.width, 10);
        if (px > 0 && col.width.endsWith('px')) widths[field] = px;
      }
    });
    return { columns: fieldNames, richColumns: rich, colWidths: widths };
  }, [effectiveLegacyCols]);

  const columns: string[] = mappedColumns?.columns ?? (isLegacyColumnArray ? [] : (props.columns as string[]) ?? []);
  const richColumns = props.richColumns ?? mappedColumns?.richColumns;
  const colWidths = props.colWidths ?? mappedColumns?.colWidths ?? {};
  const fieldBehaviors = props.fieldBehaviors ?? {};
  const fieldSpecs = props.fieldSpecs ?? {};
  const numId = props.numId ?? _numId;
  const fontSize = props.fontSize ?? 13;

  // --- Column context menu state ---
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; field: string; colIdx: number } | null>(null);
  const [contextSubmenu, setContextSubmenu] = useState<'add' | 'views' | null>(null);

  // --- Self-managed state for convenience mode ---
  const [selfSort, setSelfSort] = useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);
  const [selfSelectedId, setSelfSelectedId] = useState<number | null>(null);
  const [selfSelectedRowIds, setSelfSelectedRowIds] = useState<Set<number>>(new Set());

  const isConvenience = props.onSelectRecord == null; // no explicit handler = convenience mode

  const sort = isConvenience ? selfSort : (props.sort ?? null);
  const selectedId = isConvenience ? selfSelectedId : (props.selectedId ?? null);
  const selectedRowIds = isConvenience
    ? (props.enableSelection ? selfSelectedRowIds : new Set<number>())
    : (props.selectedRowIds ?? new Set<number>());

  // --- Search filtering (convenience mode) ---
  const effectiveSearchTerm = props.externalSearchTerm ?? '';
  const searchedRecords = useMemo(() => {
    if (!effectiveSearchTerm.trim()) return inputData;
    const fragments = parseFragments(effectiveSearchTerm);
    return inputData.filter((row: any) => matchesFragments(row, fragments));
  }, [inputData, effectiveSearchTerm]);

  const records = isConvenience ? searchedRecords : inputData;

  // --- Record map ---
  const recordMap = useMemo(() => {
    const m = new Map<number, any>();
    records.forEach((r: any) => {
      const id = numId(r.id);
      if (id !== null) m.set(id, r);
    });
    return m;
  }, [records, numId]);

  // --- Convenience handlers ---
  const handleSort = useCallback((field: string, multiSort?: boolean) => {
    if (props.onSort) {
      props.onSort(field, multiSort);
    } else {
      setSelfSort((prev) => {
        if (prev?.field === field) {
          return prev.direction === 'asc' ? { field, direction: 'desc' } : null;
        }
        return { field, direction: 'asc' };
      });
    }
  }, [props.onSort]);

  const handleSelectRecord = useCallback((id: number) => {
    if (props.onSelectRecord) {
      props.onSelectRecord(id);
    } else {
      setSelfSelectedId(id);
      if (props.onRowClicked) {
        const row = recordMap.get(id);
        if (row) props.onRowClicked(row);
      }
    }
  }, [props.onSelectRecord, props.onRowClicked, recordMap]);

  const handleToggleRow = useCallback((id: number) => {
    if (props.onToggleRow) {
      props.onToggleRow(id);
    } else {
      setSelfSelectedRowIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id); else next.add(id);
        return next;
      });
    }
  }, [props.onToggleRow]);

  const onColumnDrop = props.onColumnDrop ?? (() => {});
  const onResizeStart = props.onResizeStart ?? (() => {});
  const onWidthClick = props.onWidthClick;
  const onCellEdit = props.onCellEdit;

  const { pinnedColumn, colorRules, groupByField } = props;

  // Fire onSelectionChange when selectedRowIds changes (convenience mode)
  useEffect(() => {
    if (!props.onSelectionChange || !isConvenience) return;
    const rows: any[] = [];
    selfSelectedRowIds.forEach((id) => { const r = recordMap.get(id); if (r) rows.push(r); });
    props.onSelectionChange(rows);
  }, [selfSelectedRowIds, recordMap, props.onSelectionChange, isConvenience]);

  // Build rich column lookup for custom cell renderers
  const richColMap = useMemo(() => {
    if (!richColumns) return new Map<string, RichColumn>();
    return new Map(richColumns.map((c) => [c.name, c]));
  }, [richColumns]);
  // --- Column filters ---
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [showFilters, setShowFilters] = useState(props.externalShowFilters ?? false);
  const filterDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setFiltersAndNotify = useCallback((updater: (prev: Record<string, string>) => Record<string, string>) => {
    setFilters((prev) => {
      const next = updater(prev);
      // Debounce server-side filter callback (500ms after last keystroke)
      if (props.onFilterChange) {
        if (filterDebounce.current) clearTimeout(filterDebounce.current);
        filterDebounce.current = setTimeout(() => {
          const active = Object.fromEntries(Object.entries(next).filter(([, v]) => v.trim()));
          props.onFilterChange!(active);
        }, 500);
      }
      return next;
    });
  }, [props.onFilterChange]);

  // --- Inline edit ---
  const [editCell, setEditCell] = useState<{ rid: number; field: string; was: string } | null>(null);
  const [cellResult, setCellResult] = useState<{ rid: number; field: string; error?: string } | null>(null);
  const lastClickedIdx = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef<HTMLInputElement>(null);

  // --- Multi-sort ---
  const [multiSorts] = useState<SortSpec[]>([]);

  // --- Drag reorder ---
  const [dragField, setDragField] = useState<string | null>(null);


  // --- Duplicate detection ---
  const [showDupes, setShowDupes] = useState(props.externalShowDupes ?? false);
  const dupeIds = useMemo(() => showDupes ? detectDuplicates(records, columns) : new Set<number>(), [showDupes, records, columns]);

  // Sync external filter/dupes toggle from parent
  useEffect(() => { if (props.externalShowFilters !== undefined) setShowFilters(props.externalShowFilters); }, [props.externalShowFilters]);
  useEffect(() => { if (props.externalShowDupes !== undefined) setShowDupes(props.externalShowDupes); }, [props.externalShowDupes]);

  // --- Filtered records ---
  const filteredRecords = useMemo(() => {
    if (!Object.values(filters).some((v) => v.trim())) return records;
    return records.filter((rec) =>
      Object.entries(filters).every(([field, filterVal]) => {
        if (!filterVal.trim()) return true;
        const v = String(rec[field] ?? '').toLowerCase();
        return v.includes(filterVal.toLowerCase());
      })
    );
  }, [records, filters]);

  // --- Footer: Σ of the rows on screen, per column as cellFormat.footerKind says ---
  const totals = useMemo(() => {
    const result: Record<string, { kind: FooterKind; value: number }> = {};
    columns.forEach((f) => {
      const kind = footerKind(f, fieldBehaviors[f]);
      if (!kind) return;
      let sum = 0;
      let count = 0;
      filteredRecords.forEach((rec) => {
        const v = Number(valueAt(rec, f));
        if (valueAt(rec, f) != null && valueAt(rec, f) !== '' && !isNaN(v)) { sum += v; count++; }
      });
      result[f] = { kind, value: kind === 'count' ? count : kind === 'average' ? (count ? sum / count : 0) : sum };
    });
    return result;
  }, [filteredRecords, columns, fieldBehaviors]);

  // --- Inline edit handlers ---
  // A cell the list can edit. Edit-in-list keeps to plain values: a date needs its date widget and
  // a link its search, so those stay in the form.
  const cellEditable = useCallback((field: string, value: unknown) => {
    const b = fieldBehaviors[field];
    if (b?.type === 'readonly' || b?.type === 'timestamp') return false;
    if (!props.editInList) return true;
    if (b?.calculated || field === 'id' || field.includes('.') || /^dt_|_id$/.test(field)) return false;
    if (props.fieldEditable && !props.fieldEditable(field)) return false;
    if (b?.type && !['text', 'string', 'number', 'currency', 'select', 'email', 'phone'].includes(b.type)) return false;
    return value == null || typeof value !== 'object';
  }, [fieldBehaviors, props.editInList, props.fieldEditable]);

  const startEdit = useCallback((rid: number, field: string, currentValue: unknown) => {
    if (!onCellEdit || !cellEditable(field, currentValue)) return;
    const was = typeof currentValue === 'object' && currentValue !== null ? JSON.stringify(currentValue) : String(currentValue ?? '');
    setEditCell({ rid, field, was });
    setCellResult(null);
    setEditValue(was);
    setTimeout(() => editRef.current?.focus(), 50);
  }, [onCellEdit, cellEditable]);

  const commitEdit = useCallback((moveDirection?: 'right' | 'down') => {
    if (!editCell || !onCellEdit) return;
    let val: unknown = editValue;
    const beh = fieldBehaviors[editCell.field];
    if (beh?.type === 'number' || beh?.type === 'currency') val = parseFloat(editValue) || 0;
    else if (beh?.type === 'boolean') val = editValue === 'true' || editValue === '1';
    // Saved the moment the cell is left — and only when it changed.
    if (editValue !== editCell.was) {
      const { rid, field } = editCell;
      const saving = onCellEdit(rid, field, val);
      if (saving) {
        saving.then(() => {
          setCellResult({ rid, field });
          setTimeout(() => setCellResult((c) => (c && c.rid === rid && c.field === field && !c.error ? null : c)), 1200);
        }, (err: any) => setCellResult({ rid, field, error: String(err?.message || err) }));
      }
    }

    if (moveDirection && filteredRecords.length > 0) {
      const editableColumns = columns.filter(f => {
        if (props.editInList) return cellEditable(f, undefined);
        const b = fieldBehaviors[f];
        return b && b.type !== 'readonly' && b.type !== 'timestamp' && !b.calculated;
      });
      const colIdx = editableColumns.indexOf(editCell.field);
      const rowIdx = filteredRecords.findIndex(r => numId(r.id) === editCell.rid);

      if (moveDirection === 'right' && colIdx >= 0) {
        // Tab → next editable column in same row, or first column of next row
        if (colIdx < editableColumns.length - 1) {
          const nextField = editableColumns[colIdx + 1];
          const val2 = filteredRecords[rowIdx]?.[nextField];
          startEdit(editCell.rid, nextField, val2);
          return;
        } else if (rowIdx < filteredRecords.length - 1) {
          const nextRid = numId(filteredRecords[rowIdx + 1]?.id);
          if (nextRid !== null) {
            const nextField = editableColumns[0];
            const val2 = filteredRecords[rowIdx + 1]?.[nextField];
            startEdit(nextRid, nextField, val2);
            return;
          }
        }
      } else if (moveDirection === 'down' && rowIdx >= 0) {
        // Enter → same column, next row
        if (rowIdx < filteredRecords.length - 1) {
          const nextRid = numId(filteredRecords[rowIdx + 1]?.id);
          if (nextRid !== null) {
            const val2 = filteredRecords[rowIdx + 1]?.[editCell.field];
            startEdit(nextRid, editCell.field, val2);
            return;
          }
        }
      }
    }
    setEditCell(null);
  }, [editCell, editValue, onCellEdit, fieldBehaviors, columns, filteredRecords, numId, cellEditable, props.editInList]);

  const cancelEdit = useCallback(() => setEditCell(null), []);

  // Focus edit input when it appears
  useEffect(() => {
    if (editCell) editRef.current?.focus();
  }, [editCell]);

  // --- Row color ---
  const getRowStyle = useCallback((rec: any): React.CSSProperties => {
    if (!colorRules?.length) return {};
    for (const rule of colorRules) {
      if (matchesRule(rec, rule)) {
        return {
          background: rule.bg,
          color: rule.text,
          fontWeight: rule.bold ? 700 : undefined,
        };
      }
    }
    return {};
  }, [colorRules]);

  // --- A cell being edited: its editor. Every other cell is its column's render. ---
  const cellType = (f: string) => ({ type: fieldBehaviors[f]?.type, format: fieldSpecs[f]?.format, precision: fieldBehaviors[f]?.precision });
  const editorFor = (rid: number | null, field: string): React.ReactNode | undefined => {
    if (!(editCell?.rid === rid && editCell?.field === field)) return undefined;
    const beh = fieldBehaviors[field];
    if (beh?.type === 'select' && beh.options) {
      return (
        <select value={editValue} onChange={(e) => setEditValue(e.target.value)}
          onBlur={() => commitEdit()} onKeyDown={(e) => { if (e.key === 'Escape') cancelEdit(); if (e.key === 'Enter') commitEdit(); }}
          ref={editRef as any} autoFocus className="dg-cell-edit">
          <option value="">--</option>
          {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    return (
      <input ref={editRef} value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={() => commitEdit()}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); commitEdit('down'); }
          if (e.key === 'Escape') cancelEdit();
          if (e.key === 'Tab') { e.preventDefault(); commitEdit('right'); }
        }}
        className="dg-cell-edit"
      />
    );
  };

  // --- Row click handler: plain=select+check, shift=range, ctrl/cmd=toggle ---
  const handleRowClick = useCallback((e: React.MouseEvent, rid: number | null, rowIdx: number, rows: any[]) => {
    if (rid === null) return;

    if (e.shiftKey && lastClickedIdx.current !== null) {
      // Shift-click: select range between last clicked and current
      const start = Math.min(lastClickedIdx.current, rowIdx);
      const end = Math.max(lastClickedIdx.current, rowIdx);
      const rangeIds = new Set(selectedRowIds);
      for (let i = start; i <= end; i++) {
        const id = numId(rows[i]?.id);
        if (id !== null) rangeIds.add(id);
      }
      if (props.onToggleRow) {
        // External mode — set all at once via parent
        rangeIds.forEach((id) => { if (!selectedRowIds.has(id)) props.onToggleRow!(id); });
      } else {
        setSelfSelectedRowIds(rangeIds);
      }
    } else if (e.metaKey || e.ctrlKey) {
      // Ctrl/Cmd-click: toggle this row without affecting others
      handleToggleRow(rid);
    } else {
      // Plain click: select only this row (clears others). WC standard.
      handleSelectRecord(rid);
    }
    lastClickedIdx.current = rowIdx;
  }, [selectedRowIds, handleSelectRecord, handleToggleRow, numId, props.onToggleRow]);

  // A list whose double-click opens the record takes the WC List Standard's gestures, the
  // same code as every panel list (useListGestures); other grids keep the handling above.
  const gestures = useListGestures<number>({
    enabled: !!props.onSelectRows,
    listRef: scrollRef,
    keys: () => Array.from(scrollRef.current?.querySelectorAll<HTMLElement>('tr.dg-row[data-row-key]') ?? [])
      .map((tr) => Number(tr.dataset.rowKey)),
    selected: selectedRowIds,
    select: (next, moved) => props.onSelectRows?.(next, moved),
    open: (rid) => { if (!props.editInList) handleSelectRecord(rid); },
    openWindow: (rid) => { const row = recordMap.get(rid); if (row) props.onOpenWindow?.(row); },
    busy: () => !!editCell,
    help: props.editInList ? LIST_HELP + EDIT_IN_LIST_HELP : LIST_HELP,
  });

  // Compute effective width per column — every column gets an explicit width
  const DEFAULT_COL_W = 120;
  const INDICATOR_W = 8;
  const effectiveColWidths = useMemo(() => {
    const w: Record<string, number> = {};
    columns.forEach((f) => { w[f] = colWidths[f] || DEFAULT_COL_W; });
    return w;
  }, [columns, colWidths]);
  const tableWidth = useMemo(() =>
    INDICATOR_W + columns.reduce((sum, f) => sum + effectiveColWidths[f], 0),
    [columns, effectiveColWidths]);

  // --- The columns: one per field, formatted and aligned as in every list (cellFormat) ---
  const gridColumns = useMemo<DbColumnDef<any>[]>(() => columns.map((f) => {
    const rich = richColMap.get(f);
    const sample = records.slice(0, 5).map((r) => r[f]).find((v) => v != null);
    return {
      key: f,
      label: fieldSpecs[f]?.label || fieldBehaviors[f]?.label || fieldLabel(f),
      width: effectiveColWidths[f],
      align: cellAlign(f, { ...cellType(f), align: fieldSpecs[f]?.align }, sample),
      calculated: !!fieldBehaviors[f]?.calculated,
      headerStyle: headerStyle(fieldBehaviors[f]?.type),
      render: rich?.cell
        ? (rec: any) => rich.cell!(rec)
        : (rec: any) => formatCell(rich?.selector ? rich.selector(rec) : valueAt(rec, f), f, cellType(f)),
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [columns, richColMap, fieldSpecs, fieldBehaviors, effectiveColWidths, records]);

  // A list that opens on double-click marks the open record apart from the selection.
  const opensApart = !!props.onSelectRows;
  const rowProps = (rec: any, idx: number) => {
    const rid = numId(rec.id);
    const isActive = rid !== null && selectedId === rid;
    const isChecked = rid !== null && selectedRowIds.has(rid);
    const ruleStyle = getRowStyle(rec);
    const classes: string[] = [];
    if (isChecked || (isActive && !opensApart)) classes.push('dg-row--checked');
    else if (idx % 2 === 1) classes.push('dg-row--striped');
    if (rid !== null && dupeIds.has(rid)) classes.push('dg-row--dupe');
    if (isActive && opensApart) classes.push('dg-row--open');
    return {
      'data-rid': rid,
      'aria-selected': isChecked || (isActive && !opensApart),
      'aria-current': isActive && opensApart ? true : undefined,
      className: classes.join(' '),
      style: ruleStyle.background ? { background: ruleStyle.background, color: ruleStyle.color, fontWeight: ruleStyle.fontWeight } : undefined,
      ...(opensApart && rid !== null ? gestures.rowProps(rid) : {
        onClick: (e: React.MouseEvent) => handleRowClick(e, rid, idx, filteredRecords),
        onDoubleClick: () => { if (rid !== null) { handleSelectRecord(rid); props.onRowDoubleClicked?.(rec); } },
      }),
    } as Record<string, unknown>;
  };

  const cellProps = (rec: any, col: DbColumnDef<any>): React.TdHTMLAttributes<HTMLTableCellElement> => {
    const f = col.key;
    const rid = numId(rec.id);
    const isPinned = columns[0] === f && pinnedColumn === f;
    const canEdit = !!onCellEdit && cellEditable(f, rec[f]);
    const result = cellResult && cellResult.rid === rid && cellResult.field === f ? cellResult : null;
    const classes: string[] = [];
    if (isPinned) classes.push('dg-td--pinned');
    if (isPinned && rid !== null && selectedId === rid) classes.push('dg-td--active');
    if (result) classes.push(result.error ? 'dg-td--failed' : 'dg-td--saved');
    if (props.editInList && canEdit) classes.push('dg-td--editable');
    return {
      className: classes.join(' '),
      'aria-readonly': canEdit ? false : undefined,
      // A list whose double-click opens the record edits a cell only with edit-in-list on.
      onDoubleClick: props.onSelectRows && !props.editInList ? undefined : (e) => { if (rid !== null && !e.altKey) startEdit(rid, f, rec[f]); },
      // Cmd-click toggles the row; Cmd-Option-click is the cell's own (an ida's image, Bill 2026-10-31).
      onClick: props.onCellClick ? (e: React.MouseEvent) => { if ((e.metaKey || e.ctrlKey) && e.altKey && props.onCellClick) { e.stopPropagation(); props.onCellClick(e, f, rec); } } : undefined,
      title: result?.error ? `Not saved: ${result.error}` : cellTitle(rec[f], f, cellType(f)),
    };
  };

  // --- Export ---
  const exportJSON = useCallback(() => {
    const exportData = filteredRecords.map((rec) =>
      Object.fromEntries(columns.map((f) => [f, rec[f]]))
    );
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json;charset=utf-8;' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `export_${new Date().toISOString().slice(0, 10)}.json`;
    a.click(); URL.revokeObjectURL(a.href);
  }, [filteredRecords, columns]);

  const exportCSV = useCallback(() => {
    const header = columns.join(',');
    const lines = filteredRecords.map((r) =>
      columns.map((f) => { const s = typeof r[f] === 'object' && r[f] !== null ? JSON.stringify(r[f]) : String(r[f] ?? ''); return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s; }).join(',')
    );
    const blob = new Blob([[header, ...lines].join('\n')], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `export_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(a.href);
  }, [filteredRecords, columns]);

  // --- Drag-to-scroll horizontal panning ---

  const dragScrollRef = useRef<{ startX: number; startScrollLeft: number } | null>(null);

  // --- Early returns (AFTER all hooks) ---
  if (props.loading) {
    return (
      <div className="flex items-center justify-center p-20" data-wc="datagrid-loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  if (isConvenience && records.length === 0) {
    return (
      <div className="flex items-center justify-center p-12" data-wc="datagrid-empty">
        <div className="text-center">
          <p className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
            {props.noDataMessage || 'No data available'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {effectiveSearchTerm
              ? 'Try adjusting your search or filters'
              : 'Start by adding some data'}
          </p>
        </div>
      </div>
    );
  }

  // --- A column's header: sort, Shift-drag reorder, right-click menu, width badge, resize ---
  const headerCell = (col: DbColumnDef<any>, ci: number) => {
    const f = col.key;
    const sortIdx = multiSorts.findIndex((m) => m.field === f);
    const sortDir = sort?.field === f ? sort.direction : null;
    const badge = (el: HTMLElement, on: boolean) => {
      const b = el.querySelector('.dg-width-badge') as HTMLElement | null;
      if (b) b.style.opacity = on ? '1' : '0';
    };
    return {
      props: {
        'aria-sort': sortDir === 'asc' ? 'ascending' : sortDir === 'desc' ? 'descending' : 'none',
        className: ci === 0 && pinnedColumn === f ? 'dg-th--pinned' : undefined,
        draggable: true,
        onDragStart: (e) => { if (props.disableReorder || !e.shiftKey) { e.preventDefault(); return; } setDragField(f); },
        onDragOver: (e) => e.preventDefault(),
        onDrop: () => { if (dragField) onColumnDrop(dragField, f); setDragField(null); },
        onMouseEnter: (e) => badge(e.currentTarget, true),
        onMouseLeave: (e) => badge(e.currentTarget, false),
        onClick: (e) => {
          if (e.shiftKey && props.onHeaderClick && fieldBehaviors[f]?.bulkEditable) {
            e.preventDefault();
            props.onHeaderClick(f);
          } else {
            handleSort(f, e.ctrlKey || e.metaKey);
          }
        },
        onContextMenu: (e) => {
          if (props.onDeleteColumn || props.onSaveLayout) {
            e.preventDefault();
            setContextMenu({ x: e.clientX, y: e.clientY, field: f, colIdx: ci });
            setContextSubmenu(null);
          }
        },
        title: fieldBehaviors[f]?.bulkEditable ? `${f} · Click to sort · Shift-click to bulk edit` : `${f} · Click to sort`,
      } as React.ThHTMLAttributes<HTMLTableCellElement>,
      content: (
        <>
          {props.headerEditField === f ? (
            <span className="dg-header-edit" onClick={(e) => e.stopPropagation()}>
              <input autoFocus type="text"
                value={props.headerEditValue || ''}
                onChange={(e) => props.onHeaderEditChange?.(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') props.onHeaderEditApply?.(); if (e.key === 'Escape') props.onHeaderEditCancel?.(); }}
                className="dg-header-edit-input"
              />
              <span className="dg-header-edit-ok" onClick={() => props.onHeaderEditApply?.()}>✓</span>
              <span className="dg-header-edit-cancel" onClick={() => props.onHeaderEditCancel?.()}>✕</span>
            </span>
          ) : (
            <>
              <span className={fieldBehaviors[f]?.bulkEditable ? 'dg-th-name--bulk' : undefined} style={col.headerStyle}>{col.label}</span>
              {sortDir && <span className="dg-sort-arrow">{sortDir === 'asc' ? '↑' : '↓'}</span>}
              {sortIdx >= 0 && <span className="dg-sort-order">({sortIdx + 1})</span>}
            </>
          )}
          {/* Width badge — visible on hover, click to type */}
          {colWidths[f] && onWidthClick && (
            <span className="dg-width-badge"
              onClick={(e) => { e.stopPropagation(); onWidthClick(f, e.currentTarget); }}
              title="Click to set width"
            >{colWidths[f]}</span>
          )}
          <span className="dg-resize-handle"
            onMouseDown={(e) => onResizeStart(f, e)} onClick={(e) => e.stopPropagation()}
            onDoubleClick={(e) => { e.stopPropagation(); onWidthClick?.(f, e.currentTarget as HTMLElement); }}
          />
        </>
      ),
    };
  };

  // The scroll box: the gestures' list props and sideways drag-scrolling when the table overflows.
  const containerProps: React.HTMLAttributes<HTMLDivElement> = {
    ...gestures.listProps,
    style: { cursor: tableWidth > (scrollRef.current?.clientWidth ?? Infinity) ? 'grab' : undefined },
    onMouseDown: (e) => {
      if (!scrollRef.current || tableWidth <= scrollRef.current.clientWidth) return;
      if (e.button !== 0) return;
      // Don't interfere with resize handles, edit inputs, or header clicks
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'BUTTON') return;
      const target = e.target as HTMLElement;
      if (target.style.cursor === 'col-resize' || target.closest('[style*="col-resize"]')) return;
      dragScrollRef.current = { startX: e.clientX, startScrollLeft: scrollRef.current.scrollLeft };
    },
    onMouseMove: (e) => {
      if (!dragScrollRef.current || !scrollRef.current) return;
      const dx = e.clientX - dragScrollRef.current.startX;
      if (Math.abs(dx) > 3) {
        scrollRef.current.style.cursor = 'grabbing';
        scrollRef.current.scrollLeft = dragScrollRef.current.startScrollLeft - dx;
      }
    },
    onMouseUp: () => { if (scrollRef.current) scrollRef.current.style.cursor = ''; dragScrollRef.current = null; },
    onMouseLeave: () => { if (scrollRef.current) scrollRef.current.style.cursor = ''; dragScrollRef.current = null; },
  };

  // --- Toolbar ---
  const toolbar = (
    <div className="dg-toolbar">
      <button onClick={() => setShowFilters(!showFilters)}
        className={`dg-toolbar-btn${showFilters ? ' dg-toolbar-btn--active-blue' : ''}`}>
        Filter
      </button>
      <button onClick={() => setShowDupes(!showDupes)}
        className={`dg-toolbar-btn${showDupes ? ' dg-toolbar-btn--active-gold' : ''}`}>
        Dupes{showDupes && dupeIds.size > 0 ? ` (${dupeIds.size})` : ''}
      </button>
      <button onClick={exportCSV} className="dg-toolbar-btn">CSV</button>
      <button onClick={exportJSON} className="dg-toolbar-btn">JSON</button>
      <button onClick={() => window.print()} className="dg-toolbar-btn">Print</button>
      {Object.values(filters).some((v) => v.trim()) && (
        <button onClick={() => setFilters({})} className="dg-toolbar-btn dg-toolbar-btn--danger">
          Clear Filters
        </button>
      )}
      <span className="dg-toolbar-spacer" />
      <span>{filteredRecords.length}{filteredRecords.length !== records.length ? ` of ${records.length}` : ''} rows</span>
    </div>
  );

  return (
    <div className="dg-root" role="grid" aria-label="Data grid" aria-rowcount={filteredRecords.length} aria-colcount={columns.length} style={{ '--dg-fs': props.fontSize ? `${fontSize}px` : 'var(--db-font-size, 13px)', '--dg-fs-sm': props.fontSize ? `${fontSize - 1}px` : 'calc(var(--db-font-size, 13px) - 1px)', '--dg-fs-xs': props.fontSize ? `${fontSize - 2}px` : 'calc(var(--db-font-size, 13px) - 2px)' } as React.CSSProperties}>
      {!props.hideToolbar && toolbar}
        <DbColumnsTable<any>
          columns={gridColumns}
          rows={filteredRecords}
          rowKey={(rec) => numId(rec.id) ?? JSON.stringify(rec).slice(0, 40)}
          fixedWidths
          headerWhenEmpty
          pinnedIndicator={!!pinnedColumn}
          headerCell={headerCell}
          headerRows={<>
            {/* Filter row */}
            {showFilters && (
              <tr className="dg-filter-row">
                <th className="dg-filter-cell" />
                {columns.map((f) => {
                  const beh = fieldBehaviors[f];
                  if (beh?.type === 'select' && beh.options) {
                    return (
                      <th key={f} className="dg-filter-cell">
                        <select value={filters[f] || ''} onChange={(e) => setFiltersAndNotify((p) => ({ ...p, [f]: e.target.value }))}
                          className="dg-filter-select">
                          <option value="">All</option>
                          {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </th>
                    );
                  }
                  return (
                    <th key={f} className="dg-filter-cell">
                      <input type="text" value={filters[f] || ''} placeholder="..."
                        onChange={(e) => setFiltersAndNotify((p) => ({ ...p, [f]: e.target.value }))}
                        className="dg-filter-input"
                      />
                    </th>
                  );
                })}
              </tr>
            )}
          </>}
          footer={Object.keys(totals).length > 0 ? (
              <tr className="dg-tfoot-row" role="row">
                <td className="dg-tfoot-sigma">Σ</td>
                {columns.map((f) => {
                  const t_data = totals[f];
                  if (!t_data) return <td key={f} className="dg-tfoot-empty" />;
                  const shown = t_data.kind === 'count' ? String(t_data.value)
                    : formatCell(t_data.value, f, { ...cellType(f), type: fieldBehaviors[f]?.type === 'currency' ? 'currency' : 'number',
                                                     precision: t_data.kind === 'average' ? 2 : cellType(f).precision });
                  return <td key={f} className="dg-tfoot-cell" style={{ textAlign: 'right' }}
                    title={t_data.kind === 'sum' ? 'Sum of the rows shown' : t_data.kind === 'average' ? 'Average of the rows shown' : 'Count of the rows shown'}>
                    {t_data.kind === 'sum' ? shown : `${t_data.kind === 'average' ? 'avg' : 'n'} ${shown}`}</td>;
                })}
              </tr>
            ) : undefined}
          rowProps={rowProps}
          marked={(rec) => { const rid = numId(rec.id); return rid !== null && selectedRowIds.has(rid); }}
          cellProps={cellProps}
          renderCell={(rec, col) => editorFor(numId(rec.id), col.key)}
          groupBy={groupByField ? (rec) => String(rec[groupByField] ?? '(empty)') : undefined}
          groupLabel={(g, recs) => `${groupByField}: ${g} (${recs.length})`}
          collapsibleGroups
          empty={<div className="dg-empty">{Object.values(filters).some((v) => v.trim()) ? 'No records match filters.' : 'No records.'}</div>}
          scroll
          containerRef={scrollRef}
          containerProps={containerProps}
        />
      {/* Custom footer bar (line card: Lns/Items/Deposit/Backlog/Total + buttons) */}
      {props.footerBar}

      {/* Panel content (line card: Inventory/Spec/XRef/Margin panels) */}
      {props.panelContent}

      {/* Column context menu — wc2 right-click pattern */}
      {contextMenu && (
        <>
          <div className="dg-ctx-backdrop"
            onClick={() => { setContextMenu(null); setContextSubmenu(null); }} />
          <div className="dg-ctx-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
            {props.onDeleteColumn && (
              <div className="dg-ctx-item"
                onMouseEnter={() => setContextSubmenu(null)}
                onClick={() => { props.onDeleteColumn!(contextMenu.field); setContextMenu(null); }}>
                Delete Column
              </div>
            )}
            {props.onAddColumn && props.allFields && (
              <div className="dg-ctx-item dg-ctx-item--submenu"
                onMouseEnter={() => setContextSubmenu('add')}>
                Add Column ▸
                {contextSubmenu === 'add' && (
                  <div className="dg-ctx-submenu">
                    {(props.allFields || [])
                      .filter((af) => !columns.includes(af))
                      .sort()
                      .map((af) => (
                        <div key={af} className="dg-ctx-submenu-item"
                          onClick={() => { props.onAddColumn!(af, contextMenu.colIdx + 1); setContextMenu(null); }}>
                          {af}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
            {(props.onDeleteColumn || props.onAddColumn) && (props.onSaveLayout || props.onSaveLayoutAs) && (
              <div className="dg-ctx-separator" />
            )}
            {props.onSaveLayout && (
              <div className="dg-ctx-item"
                onMouseEnter={() => setContextSubmenu(null)}
                onClick={() => { props.onSaveLayout!(); setContextMenu(null); }}>
                Save Layout
              </div>
            )}
            {props.onSaveLayoutAs && (
              <div className="dg-ctx-item"
                onMouseEnter={() => setContextSubmenu(null)}
                onClick={() => { props.onSaveLayoutAs!(); setContextMenu(null); }}>
                Save As New…
              </div>
            )}
            {props.namedViews && props.namedViews.length > 0 && props.onLoadView && (
              <>
                <div className="dg-ctx-separator" />
                {props.namedViews.map((v) => (
                  <div key={v.name} className="dg-ctx-item"
                    onMouseEnter={() => setContextSubmenu(null)}
                    onClick={() => { props.onLoadView!(v.name); setContextMenu(null); }}>
                    {v.name}
                  </div>
                ))}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
