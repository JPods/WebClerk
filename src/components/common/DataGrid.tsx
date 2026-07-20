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
 * Replaces the inline table in AdminWorkbench.
 * Reusable in any page that needs a data table.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as XLSX from 'xlsx';
import { parseFragments, matchesFragments } from '@/utils/searchFragments';

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
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  onSort?: (field: string, multiSort?: boolean) => void;
  onColumnDrop?: (dragField: string, targetField: string) => void;
  onResizeStart?: (field: string, e: React.MouseEvent) => void;
  onCellEdit?: (recordId: number, field: string, value: unknown) => void;
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
  /** Alias for records — pass data here for backward compat */
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
  /** Hide the built-in toolbar (Filter/Dupes/CSV/Excel/Print) — use when parent provides its own */
  hideToolbar?: boolean;
  /** Expose filter toggle to parent */
  onToggleFilters?: (show: boolean) => void;
  /** Expose dupes toggle to parent */
  onToggleDupes?: (show: boolean) => void;
  /** External control of filter visibility */
  externalShowFilters?: boolean;
  /** External control of dupes visibility */
  externalShowDupes?: boolean;

  // --- Tree/hierarchy support (BOM, org charts, category trees) ---
  treeColumn?: string;        // which column gets indent + expand/collapse chevron
  levelField?: string;        // data field carrying the depth number (e.g., 'level')
  childFlag?: string;         // data field indicating row has children (e.g., 'is_subassembly')
  treeIndent?: number;        // px per level (default 20)

  // --- Ignored props (accepted but unused, for backward compat during migration) ---
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

const DEFAULT_THEME = {
  bg: '#f8f9fa', surface: '#ffffff', surfaceAlt: '#f1f3f5',
  border: '#dee2e6', borderLight: '#e9ecef',
  text: '#212529', textMuted: '#6c757d', textDim: '#adb5bd',
  accent: '#0d6efd', accentGreen: '#198754', accentGold: '#fd7e14',
  accentRed: '#dc3545', accentPurple: '#6f42c1',
  btnBg: '#ffffff', btnPrimary: '#0d6efd', btnSave: '#198754',
  btnSaveBorder: '#198754', btnDangerBorder: '#dc3545',
  inputBg: '#ffffff', inputBorder: '#ced4da',
  rowHover: '#f1f3f5', rowActive: '#cfe2ff', rowChecked: '#fff3cd',
  resizeHandle: '#0d6efd',
};

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
    const fieldNames = effectiveLegacyCols.map((c: any, i: number) => _getFieldName(c, i));
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

  const columns = mappedColumns?.columns ?? (isLegacyColumnArray ? [] : (props.columns as string[]) ?? []);
  const richColumns = props.richColumns ?? mappedColumns?.richColumns;
  const colWidths = props.colWidths ?? mappedColumns?.colWidths ?? {};
  const fieldBehaviors = props.fieldBehaviors ?? {};
  const fieldSpecs = props.fieldSpecs ?? {};
  const numId = props.numId ?? _numId;
  const t = props.theme ?? DEFAULT_THEME;
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
    return inputData.filter((row: any) => {
      const text = Object.values(row).filter((v: any) => v != null).map(String).join(' ');
      return matchesFragments(text, fragments);
    });
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

  const handleSelectAll = useCallback(() => {
    if (props.onSelectAll) {
      props.onSelectAll();
    } else {
      const all = new Set<number>();
      records.forEach((r: any) => { const id = numId(r.id); if (id !== null) all.add(id); });
      setSelfSelectedRowIds(all);
    }
  }, [props.onSelectAll, records, numId]);

  const handleClearSelection = useCallback(() => {
    if (props.onClearSelection) {
      props.onClearSelection();
    } else {
      setSelfSelectedRowIds(new Set());
    }
  }, [props.onClearSelection]);

  const onColumnDrop = props.onColumnDrop ?? ((_a: string, _b: string) => {});
  const onResizeStart = props.onResizeStart ?? ((_f: string, _e: React.MouseEvent) => {});
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

  // --- Inline edit ---
  const [editCell, setEditCell] = useState<{ rid: number; field: string } | null>(null);
  const lastClickedIdx = useRef<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef<HTMLInputElement>(null);

  // --- Multi-sort ---
  const [multiSorts, setMultiSorts] = useState<SortSpec[]>([]);

  // --- Drag reorder ---
  const [dragField, setDragField] = useState<string | null>(null);

  // --- Grouping ---
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // --- Tree / hierarchy state ---
  const [collapsedNodes, setCollapsedNodes] = useState<Set<number>>(new Set());
  const treeColumn = props.treeColumn || null;
  const levelField = props.levelField || 'level';
  const childFlag = props.childFlag || 'is_subassembly';
  const treeIndent = props.treeIndent || 20;

  const toggleTreeNode = useCallback((rowIdx: number) => {
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(rowIdx)) next.delete(rowIdx); else next.add(rowIdx);
      return next;
    });
  }, []);

  // Filter out rows hidden by collapsed parents
  const treeFilteredRecords = useMemo(() => {
    if (!treeColumn) return null; // not in tree mode
    const result: Array<{ rec: any; originalIdx: number }> = [];
    let skipBelow = -1; // skip rows deeper than this level
    for (let i = 0; i < records.length; i++) {
      const level = Number(records[i][levelField] ?? 0);
      if (skipBelow >= 0 && level > skipBelow) continue;
      skipBelow = -1; // reset skip
      result.push({ rec: records[i], originalIdx: i });
      // If this node is collapsed and has children, skip its descendants
      if (collapsedNodes.has(i) && records[i][childFlag]) {
        skipBelow = level;
      }
    }
    return result;
  }, [treeColumn, records, levelField, childFlag, collapsedNodes]);

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

  // --- Grouped records ---
  const groupedRecords = useMemo(() => {
    if (!groupByField) return null;
    const groups = new Map<string, any[]>();
    filteredRecords.forEach((rec) => {
      const key = String(rec[groupByField] ?? '(empty)');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(rec);
    });
    return groups;
  }, [filteredRecords, groupByField]);

  // --- Footer totals ---
  const totals = useMemo(() => {
    const result: Record<string, { sum: number; count: number }> = {};
    columns.forEach((f) => {
      const beh = fieldBehaviors[f];
      if (beh?.type === 'currency' || beh?.type === 'number') {
        let sum = 0;
        let count = 0;
        filteredRecords.forEach((rec) => {
          const v = Number(rec[f]);
          if (!isNaN(v)) { sum += v; count++; }
        });
        result[f] = { sum, count };
      }
    });
    return result;
  }, [filteredRecords, columns, fieldBehaviors]);

  // --- Inline edit handlers ---
  const startEdit = useCallback((rid: number, field: string, currentValue: unknown) => {
    if (!onCellEdit) return;
    const beh = fieldBehaviors[field];
    if (beh?.type === 'readonly' || beh?.type === 'timestamp') return;
    setEditCell({ rid, field });
    setEditValue(typeof currentValue === 'object' ? JSON.stringify(currentValue) : String(currentValue ?? ''));
    setTimeout(() => editRef.current?.focus(), 50);
  }, [onCellEdit, fieldBehaviors]);

  const commitEdit = useCallback(() => {
    if (!editCell || !onCellEdit) return;
    let val: unknown = editValue;
    const beh = fieldBehaviors[editCell.field];
    if (beh?.type === 'number' || beh?.type === 'currency') val = parseFloat(editValue) || 0;
    else if (beh?.type === 'boolean') val = editValue === 'true' || editValue === '1';
    onCellEdit(editCell.rid, editCell.field, val);
    setEditCell(null);
  }, [editCell, editValue, onCellEdit, fieldBehaviors]);

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

  // --- Render helpers ---
  const renderCell = (rec: any, field: string, rid: number | null) => {
    // Check for rich column custom renderer first
    const richCol = richColMap.get(field);
    if (richCol?.cell && !(editCell?.rid === rid && editCell?.field === field)) {
      return richCol.cell(rec);
    }

    const v = richCol?.selector ? richCol.selector(rec) : rec[field];
    const isEditing = editCell?.rid === rid && editCell?.field === field;

    if (isEditing) {
      const beh = fieldBehaviors[field];
      if (beh?.type === 'select' && beh.options) {
        return (
          <select value={editValue} onChange={(e) => setEditValue(e.target.value)}
            onBlur={commitEdit} onKeyDown={(e) => { if (e.key === 'Escape') cancelEdit(); if (e.key === 'Enter') commitEdit(); }}
            ref={editRef as any} autoFocus
            style={{ width: '100%', fontSize: fontSize - 1, padding: '1px 2px', background: t.inputBg, color: t.text, border: `1px solid ${t.accent}`, borderRadius: 2 }}>
            <option value="">--</option>
            {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        );
      }
      return (
        <input ref={editRef} value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitEdit();
            if (e.key === 'Escape') cancelEdit();
            if (e.key === 'Tab') { e.preventDefault(); commitEdit(); /* TODO: move to next cell */ }
          }}
          style={{ width: '100%', fontSize: fontSize - 1, padding: '1px 2px', background: t.inputBg, color: t.text, border: `1px solid ${t.accent}`, borderRadius: 2 }}
        />
      );
    }

    // Format based on FieldSpec
    const spec = fieldSpecs[field];
    if (v == null || v === '') return '';
    if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      // Multilingual or keyed object — show best display value
      // Priority: user language (en) → first string value → JSON fallback
      const lang = (navigator.language || 'en').slice(0, 2);
      if (v[lang]) return String(v[lang]);
      if (v['en']) return String(v['en']);
      const firstVal = Object.values(v).find(x => typeof x === 'string');
      if (firstVal) return String(firstVal);
      return JSON.stringify(v).slice(0, 50);
    }
    if (Array.isArray(v)) return JSON.stringify(v).slice(0, 50);
    if (spec?.format === 'currency' && typeof v === 'number') {
      return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
    }
    if (spec?.format === 'percent' && typeof v === 'number') {
      return (v >= 1 ? v : v * 100).toFixed(1) + '%';
    }
    if (spec?.format === 'date' && v) {
      try { return new Date(v).toLocaleDateString(); } catch { return String(v); }
    }
    if (spec?.format === 'number' && typeof v === 'number') {
      return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
    }
    if (spec?.format === 'phone' && typeof v === 'string' && v.replace(/\D/g, '').length >= 10) {
      const d = v.replace(/\D/g, '');
      return `(${d.slice(-10, -7)}) ${d.slice(-7, -4)}-${d.slice(-4)}`;
    }
    return String(v);
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
      // Plain click: open the record detail and clear multi-selection
      if (props.onClearSelection) props.onClearSelection();
      else setSelfSelectedRowIds(new Set());
      if (rid !== null) handleSelectRecord(rid);
      if (props.onRowClicked) props.onRowClicked(rec);
    }
    lastClickedIdx.current = rowIdx;
  }, [selectedRowIds, handleSelectRecord, handleToggleRow, numId, props.onToggleRow]);

  // --- Auto-justify: FieldSpec > fieldBehaviors > name inference > data inference ---
  const getAlign = useCallback((field: string): 'left' | 'right' | 'center' => {
    // FieldSpec align wins (user-saved or smart default)
    const spec = fieldSpecs[field];
    if (spec?.align) return spec.align;
    // Check field behaviors next
    const beh = fieldBehaviors[field];
    if (beh?.type === 'text' || beh?.type === 'email' || beh?.type === 'phone' || beh?.type === 'address' || beh?.type === 'select' || beh?.type === 'lookup' || beh?.type === 'textarea' || beh?.type === 'json' || beh?.type === 'readonly' || beh?.type === 'url') return 'left';
    if (beh?.type === 'currency' || beh?.type === 'number') return 'right';
    if (beh?.type === 'timestamp' || beh?.type === 'datetime') return 'center';
    if (beh?.type === 'boolean') return 'center';

    // Infer from field name
    const fl = field.toLowerCase();
    if (fl.startsWith('dt_') || fl.includes('date') || fl.includes('_dt')) return 'center';
    if (fl === 'total' || fl === 'balance' || fl === 'amount' || fl === 'debit' || fl === 'credit' || fl === 'price' || fl === 'cost' || fl === 'qty' || fl === 'quantity' || fl === 'version' || fl === 'priority' || fl === 'sequence' || fl === 'difficulty' || fl === 'health_rating' || fl === 'security_level' || fl === 'line_number' || fl === 'count_accessed' || fl === 'percent_complete' || fl === 'burndown' || fl === 'linkage') return 'right';
    if (fl === 'is_active' || fl === 'is_locked' || fl === 'is_deleted' || fl === 'is_archived' || fl === 'is_commission' || fl === 'is_superuser' || fl === 'is_staff' || fl === 'is_preferred') return 'center';

    // Infer from first non-null value in records
    if (records.length > 0) {
      for (const r of records.slice(0, 5)) {
        const v = r[field];
        if (v == null) continue;
        if (typeof v === 'number') return 'right';
        if (typeof v === 'boolean') return 'center';
        break;
      }
    }

    return 'left';
  }, [fieldBehaviors, records]);

  // --- Render a block of rows (used by both flat and grouped) ---
  const renderRows = (rows: any[], treeOriginalIndices?: number[]) =>
    rows.map((rec, idx) => {
      const rid = numId(rec.id);
      const isActive = rid !== null && selectedId === rid;
      const isChecked = rid !== null && selectedRowIds.has(rid);
      const isDupe = rid !== null && dupeIds.has(rid);
      const ruleStyle = getRowStyle(rec);

      // Tree state for this row
      const rowLevel = treeColumn ? Number(rec[levelField] ?? 0) : 0;
      const rowHasChildren = treeColumn ? !!rec[childFlag] : false;
      const originalIdx = treeOriginalIndices ? treeOriginalIndices[idx] : idx;
      const isCollapsed = collapsedNodes.has(originalIdx);

      return (
        <tr key={rid ?? `r-${idx}`} data-rid={rid}
          style={{
            borderBottom: `1px solid ${t.border}`,
            background: isActive ? t.rowActive : isChecked ? t.rowChecked : ruleStyle.background || 'transparent',
            color: isActive ? '#fff' : ruleStyle.color || t.text,
            fontWeight: ruleStyle.fontWeight,
            cursor: 'pointer',
            outline: isDupe ? `2px solid ${t.accentGold}` : undefined,
          }}
          onClick={(e) => handleRowClick(e, rid, idx, rows)}
          onDoubleClick={() => { if (rid !== null) { handleSelectRecord(rid); if (props.onRowDoubleClicked) props.onRowDoubleClicked(rec); } }}
          onMouseEnter={(e) => { if (!isActive && !isChecked && !ruleStyle.background) (e.currentTarget).style.background = t.rowHover; }}
          onMouseLeave={(e) => { if (!isActive && !isChecked) (e.currentTarget).style.background = ruleStyle.background || 'transparent'; }}
        >
          <td style={{ width: 8, padding: '4px 0', position: pinnedColumn ? 'sticky' as const : undefined, left: pinnedColumn ? 0 : undefined, background: isActive ? t.rowActive : isChecked ? t.rowChecked : t.surface, zIndex: pinnedColumn ? 1 : undefined }}>
            {isChecked && <div style={{ width: 4, height: '100%', minHeight: 16, background: t.accent, borderRadius: 2, margin: '0 2px' }} />}
          </td>
          {columns.map((f, ci) => {
            const spec = fieldSpecs[f];
            const doWrap = spec?.wrap === true;
            const isTreeCol = treeColumn && f === treeColumn;
            return (
            <td key={f}
              style={{
                padding: '4px 8px', overflow: 'hidden',
                textOverflow: doWrap ? undefined : 'ellipsis',
                whiteSpace: doWrap ? 'normal' : 'nowrap',
                wordBreak: doWrap ? 'break-word' : undefined,
                textAlign: getAlign(f),
                paddingLeft: isTreeCol ? `${8 + rowLevel * treeIndent}px` : undefined,
                ...(colWidths[f] ? { width: colWidths[f], minWidth: colWidths[f] } : {}),
                ...(ci === 0 && pinnedColumn === f ? { position: 'sticky' as const, left: 28, background: isActive ? t.rowActive : t.surface, zIndex: 1 } : {}),
              }}
              onDoubleClick={() => { if (rid !== null) startEdit(rid, f, rec[f]); }}
              title={String(rec[f] ?? '')}
            >
              {isTreeCol ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  {rowHasChildren ? (
                    <span style={{ cursor: 'pointer', userSelect: 'none', width: 12, display: 'inline-block' }}
                      onClick={(e) => { e.stopPropagation(); toggleTreeNode(originalIdx); }}>
                      {isCollapsed ? '▶' : '▼'}
                    </span>
                  ) : (
                    <span style={{ width: 12, display: 'inline-block', textAlign: 'center', color: t.textDim }}>·</span>
                  )}
                  {renderCell(rec, f, rid)}
                </span>
              ) : renderCell(rec, f, rid)}
            </td>
            );
          })}
        </tr>
      );
    });

  // --- Export ---
  const exportExcel = useCallback(() => {
    const exportData = filteredRecords.map((rec) =>
      Object.fromEntries(columns.map((f) => [f, typeof rec[f] === 'object' ? JSON.stringify(rec[f]) : rec[f]]))
    );
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Data');
    XLSX.writeFile(wb, `export_${new Date().toISOString().slice(0, 10)}.xlsx`);
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

  // --- Toolbar ---
  const toolbar = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px', borderBottom: `1px solid ${t.border}`, fontSize: fontSize - 2, color: t.textMuted }}>
      <button onClick={() => setShowFilters(!showFilters)}
        style={{ background: showFilters ? `${t.accent}20` : 'none', border: `1px solid ${showFilters ? t.accent : t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: showFilters ? t.accent : t.textMuted, cursor: 'pointer' }}>
        Filter
      </button>
      <button onClick={() => setShowDupes(!showDupes)}
        style={{ background: showDupes ? `${t.accentGold}20` : 'none', border: `1px solid ${showDupes ? t.accentGold : t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: showDupes ? t.accentGold : t.textMuted, cursor: 'pointer' }}>
        Dupes{showDupes && dupeIds.size > 0 ? ` (${dupeIds.size})` : ''}
      </button>
      <button onClick={exportCSV}
        style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: t.textMuted, cursor: 'pointer' }}>
        CSV
      </button>
      <button onClick={exportExcel}
        style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: t.textMuted, cursor: 'pointer' }}>
        Excel
      </button>
      <button onClick={() => window.print()}
        style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: t.textMuted, cursor: 'pointer' }}>
        Print
      </button>
      {Object.values(filters).some((v) => v.trim()) && (
        <button onClick={() => setFilters({})}
          style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '1px 6px', fontSize: fontSize - 2, color: t.accentRed, cursor: 'pointer' }}>
          Clear Filters
        </button>
      )}
      <span style={{ flex: 1 }} />
      <span>{filteredRecords.length}{filteredRecords.length !== records.length ? ` of ${records.length}` : ''} rows</span>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {!props.hideToolbar && toolbar}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ minWidth: '100%', borderCollapse: 'collapse', fontSize }}>
          <thead>
            {/* Header row */}
            <tr style={{ borderBottom: `1px solid ${t.border}`, position: 'sticky', top: 0, background: t.surface, zIndex: 2 }}>
              <th style={{ width: 8, padding: '6px 0', position: pinnedColumn ? 'sticky' as const : undefined, left: pinnedColumn ? 0 : undefined, background: t.surface, zIndex: 3 }} />
              {columns.map((f, ci) => {
                const sortIdx = multiSorts.findIndex((s) => s.field === f);
                const sortDir = sort?.field === f ? sort.direction : null;
                return (
                  <th key={f}
                    style={{
                      position: 'relative', padding: '6px 8px', textAlign: getAlign(f), color: t.textMuted,
                      fontWeight: 600, fontSize: fontSize - 1, textTransform: 'uppercase', letterSpacing: '0.04em',
                      cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      ...(colWidths[f] ? { width: colWidths[f], minWidth: colWidths[f] } : {}),
                      ...(ci === 0 && pinnedColumn === f ? { position: 'sticky' as const, left: 28, background: t.surface, zIndex: 3 } : {}),
                    }}
                    draggable
                    onDragStart={(e) => { if (!e.shiftKey) { e.preventDefault(); return; } setDragField(f); }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => { if (dragField) onColumnDrop(dragField, f); setDragField(null); }}
                    onClick={(e) => handleSort(f, e.ctrlKey || e.metaKey)}
                    onContextMenu={(e) => {
                      if (props.onDeleteColumn || props.onSaveLayout) {
                        e.preventDefault();
                        setContextMenu({ x: e.clientX, y: e.clientY, field: f, colIdx: ci });
                        setContextSubmenu(null);
                      }
                    }}
                    title="Click to sort · Ctrl-click for multi-sort · Shift-drag to reorder · Right-click for column menu"
                  >
                    {f}
                    {sortDir && <span style={{ marginLeft: 4, color: t.accent }}>{sortDir === 'asc' ? '↑' : '↓'}</span>}
                    {sortIdx >= 0 && <span style={{ marginLeft: 2, fontSize: 9, color: t.accent }}>({sortIdx + 1})</span>}
                    <span
                      style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 3, cursor: 'col-resize', background: t.borderLight }}
                      onMouseDown={(e) => onResizeStart(f, e)} onClick={(e) => e.stopPropagation()}
                      onMouseEnter={(e) => { (e.target as HTMLElement).style.background = t.resizeHandle; }}
                      onMouseLeave={(e) => { (e.target as HTMLElement).style.background = t.borderLight; }}
                    />
                  </th>
                );
              })}
            </tr>

            {/* Filter row */}
            {showFilters && (
              <tr style={{ borderBottom: `1px solid ${t.border}`, background: t.surfaceAlt }}>
                <th style={{ padding: 2 }} />
                {columns.map((f) => {
                  const beh = fieldBehaviors[f];
                  if (beh?.type === 'select' && beh.options) {
                    return (
                      <th key={f} style={{ padding: 2 }}>
                        <select value={filters[f] || ''} onChange={(e) => setFilters((p) => ({ ...p, [f]: e.target.value }))}
                          style={{ width: '100%', fontSize: fontSize - 2, padding: '2px 3px', background: t.inputBg, color: t.text, border: `1px solid ${t.inputBorder}`, borderRadius: 2 }}>
                          <option value="">All</option>
                          {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </th>
                    );
                  }
                  return (
                    <th key={f} style={{ padding: 2 }}>
                      <input type="text" value={filters[f] || ''} placeholder="..."
                        onChange={(e) => setFilters((p) => ({ ...p, [f]: e.target.value }))}
                        style={{ width: '100%', fontSize: fontSize - 2, padding: '2px 4px', background: t.inputBg, color: t.text, border: `1px solid ${t.inputBorder}`, borderRadius: 2 }}
                      />
                    </th>
                  );
                })}
              </tr>
            )}
          </thead>

          <tbody>
            {groupedRecords ? (
              // Grouped rendering
              Array.from(groupedRecords.entries()).map(([groupKey, groupRows]) => {
                const isCollapsed = collapsedGroups.has(groupKey);
                return (
                  <React.Fragment key={groupKey}>
                    <tr style={{ background: t.surfaceAlt, cursor: 'pointer' }}
                      onClick={() => setCollapsedGroups((p) => { const n = new Set(p); n.has(groupKey) ? n.delete(groupKey) : n.add(groupKey); return n; })}>
                      <td colSpan={columns.length + 1} style={{ padding: '6px 12px', fontSize: fontSize - 1, fontWeight: 700, color: t.accent }}>
                        {isCollapsed ? '▶' : '▼'} {groupByField}: {groupKey} ({groupRows.length})
                      </td>
                    </tr>
                    {!isCollapsed && renderRows(groupRows)}
                  </React.Fragment>
                );
              })
            ) : treeFilteredRecords ? (
              renderRows(
                treeFilteredRecords.map((t) => t.rec),
                treeFilteredRecords.map((t) => t.originalIdx)
              )
            ) : (
              renderRows(filteredRecords)
            )}
          </tbody>

          {/* Footer totals */}
          {Object.keys(totals).length > 0 && (
            <tfoot>
              <tr style={{ borderTop: `2px solid ${t.border}`, position: 'sticky', bottom: 0, background: t.surface, fontWeight: 700 }}>
                <td style={{ padding: '4px', fontSize: fontSize - 2, color: t.textMuted, textAlign: 'center' }}>Σ</td>
                {columns.map((f) => {
                  const t_data = totals[f];
                  if (!t_data) return <td key={f} style={{ padding: '4px 8px' }} />;
                  const beh = fieldBehaviors[f];
                  const display = beh?.type === 'currency'
                    ? t_data.sum.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
                    : t_data.sum.toLocaleString();
                  return (
                    <td key={f} style={{ padding: '4px 8px', textAlign: 'right', fontSize: fontSize - 1, color: t.accent }}>
                      {display}
                    </td>
                  );
                })}
              </tr>
            </tfoot>
          )}
        </table>

        {filteredRecords.length === 0 && (
          <div style={{ padding: 16, textAlign: 'center', color: t.textMuted, fontSize: fontSize - 1 }}>
            {Object.values(filters).some((v) => v.trim()) ? 'No records match filters.' : 'No records.'}
          </div>
        )}
      </div>

      {/* Column context menu — wc2 right-click pattern */}
      {contextMenu && (
        <>
          {/* Backdrop to close */}
          <div style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
            onClick={() => { setContextMenu(null); setContextSubmenu(null); }} />
          <div style={{
            position: 'fixed', left: contextMenu.x, top: contextMenu.y, zIndex: 9999,
            background: t.surface, border: `1px solid ${t.border}`, borderRadius: 4,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', minWidth: 180, padding: '4px 0',
            fontSize: fontSize - 1, color: t.text,
          }}>
            {/* Delete Column */}
            {props.onDeleteColumn && (
              <div style={{ padding: '6px 14px', cursor: 'pointer' }}
                onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; setContextSubmenu(null); }}
                onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}
                onClick={() => { props.onDeleteColumn!(contextMenu.field); setContextMenu(null); }}>
                Delete Column
              </div>
            )}
            {/* Add Column submenu */}
            {props.onAddColumn && props.allFields && (
              <div style={{ padding: '6px 14px', cursor: 'pointer', position: 'relative' }}
                onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; setContextSubmenu('add'); }}
                onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}>
                Add Column ▸
                {contextSubmenu === 'add' && (
                  <div style={{
                    position: 'absolute', left: '100%', top: 0,
                    background: t.surface, border: `1px solid ${t.border}`, borderRadius: 4,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)', minWidth: 160, maxHeight: 300,
                    overflowY: 'auto', padding: '4px 0',
                  }}>
                    {(props.allFields || [])
                      .filter((af) => !columns.includes(af))
                      .sort()
                      .map((af) => (
                        <div key={af} style={{ padding: '4px 12px', cursor: 'pointer' }}
                          onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; }}
                          onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}
                          onClick={() => { props.onAddColumn!(af, contextMenu.colIdx + 1); setContextMenu(null); }}>
                          {af}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
            {/* Separator */}
            {(props.onDeleteColumn || props.onAddColumn) && (props.onSaveLayout || props.onSaveLayoutAs) && (
              <div style={{ borderTop: `1px solid ${t.borderLight}`, margin: '4px 0' }} />
            )}
            {/* Save / Save As */}
            {props.onSaveLayout && (
              <div style={{ padding: '6px 14px', cursor: 'pointer' }}
                onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; setContextSubmenu(null); }}
                onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}
                onClick={() => { props.onSaveLayout!(); setContextMenu(null); }}>
                Save Layout
              </div>
            )}
            {props.onSaveLayoutAs && (
              <div style={{ padding: '6px 14px', cursor: 'pointer' }}
                onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; setContextSubmenu(null); }}
                onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}
                onClick={() => { props.onSaveLayoutAs!(); setContextMenu(null); }}>
                Save As New…
              </div>
            )}
            {/* Named views */}
            {props.namedViews && props.namedViews.length > 0 && props.onLoadView && (
              <>
                <div style={{ borderTop: `1px solid ${t.borderLight}`, margin: '4px 0' }} />
                {props.namedViews.map((v) => (
                  <div key={v.name} style={{ padding: '6px 14px', cursor: 'pointer' }}
                    onMouseEnter={(e) => { (e.currentTarget).style.background = t.rowHover; setContextSubmenu(null); }}
                    onMouseLeave={(e) => { (e.currentTarget).style.background = 'transparent'; }}
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
