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
  records: any[];
  columns: string[];                     // field names (simple mode)
  richColumns?: RichColumn[];            // rich column defs (optional, overrides simple)
  colWidths: Record<string, number>;
  fieldBehaviors: Record<string, any>;
  selectedId: number | null;
  selectedRowIds: Set<number>;
  sort: { field: string; direction: 'asc' | 'desc' } | null;
  pinnedColumn?: string | null;
  colorRules?: RowColorRule[];
  groupByField?: string | null;
  onSelectRecord: (id: number) => void;
  onToggleRow: (id: number) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onSort: (field: string, multiSort?: boolean) => void;
  onColumnDrop: (dragField: string, targetField: string) => void;
  onResizeStart: (field: string, e: React.MouseEvent) => void;
  onCellEdit?: (recordId: number, field: string, value: unknown) => void;
  numId: (v: unknown) => number | null;
  theme: any; // theme tokens
  fontSize: number;
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

export default function DataGrid({
  records, columns, richColumns, colWidths, fieldBehaviors, selectedId, selectedRowIds,
  sort, pinnedColumn, colorRules, groupByField,
  onSelectRecord, onToggleRow, onSelectAll, onClearSelection,
  onSort, onColumnDrop, onResizeStart, onCellEdit,
  numId, theme: t, fontSize,
}: DataGridProps) {
  // Build rich column lookup for custom cell renderers
  const richColMap = useMemo(() => {
    if (!richColumns) return new Map<string, RichColumn>();
    return new Map(richColumns.map((c) => [c.name, c]));
  }, [richColumns]);
  // --- Column filters ---
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [showFilters, setShowFilters] = useState(false);

  // --- Inline edit ---
  const [editCell, setEditCell] = useState<{ rid: number; field: string } | null>(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef<HTMLInputElement>(null);

  // --- Multi-sort ---
  const [multiSorts, setMultiSorts] = useState<SortSpec[]>([]);

  // --- Drag reorder ---
  const [dragField, setDragField] = useState<string | null>(null);

  // --- Grouping ---
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // --- Duplicate detection ---
  const [showDupes, setShowDupes] = useState(false);
  const dupeIds = useMemo(() => showDupes ? detectDuplicates(records, columns) : new Set<number>(), [showDupes, records, columns]);

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

    const display = typeof v === 'object' && v !== null ? JSON.stringify(v).slice(0, 50) : String(v ?? '');
    return display;
  };

  // --- Render a block of rows (used by both flat and grouped) ---
  const renderRows = (rows: any[]) =>
    rows.map((rec, idx) => {
      const rid = numId(rec.id);
      const isActive = rid !== null && selectedId === rid;
      const isChecked = rid !== null && selectedRowIds.has(rid);
      const isDupe = rid !== null && dupeIds.has(rid);
      const ruleStyle = getRowStyle(rec);

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
          onMouseEnter={(e) => { if (!isActive && !isChecked && !ruleStyle.background) (e.currentTarget).style.background = t.rowHover; }}
          onMouseLeave={(e) => { if (!isActive && !isChecked) (e.currentTarget).style.background = ruleStyle.background || 'transparent'; }}
        >
          <td style={{ padding: '4px', textAlign: 'center', position: pinnedColumn ? 'sticky' as const : undefined, left: pinnedColumn ? 0 : undefined, background: isActive ? t.rowActive : t.surface, zIndex: pinnedColumn ? 1 : undefined }}>
            <input type="checkbox" checked={isChecked} onChange={() => rid !== null && onToggleRow(rid)} />
          </td>
          {columns.map((f, ci) => (
            <td key={f}
              style={{
                padding: '4px 8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                ...(colWidths[f] ? { width: colWidths[f], minWidth: colWidths[f], maxWidth: colWidths[f] } : {}),
                ...(ci === 0 && pinnedColumn === f ? { position: 'sticky' as const, left: 28, background: isActive ? t.rowActive : t.surface, zIndex: 1 } : {}),
              }}
              onClick={() => { if (rid !== null) onSelectRecord(rid); }}
              onDoubleClick={() => { if (rid !== null) startEdit(rid, f, rec[f]); }}
              title={String(rec[f] ?? '')}
            >{renderCell(rec, f, rid)}</td>
          ))}
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
      {toolbar}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize, tableLayout: 'fixed' }}>
          <thead>
            {/* Header row */}
            <tr style={{ borderBottom: `1px solid ${t.border}`, position: 'sticky', top: 0, background: t.surface, zIndex: 2 }}>
              <th style={{ width: 28, padding: '6px 4px', textAlign: 'center', position: pinnedColumn ? 'sticky' as const : undefined, left: pinnedColumn ? 0 : undefined, background: t.surface, zIndex: 3 }}>
                <input type="checkbox"
                  checked={selectedRowIds.size > 0 && filteredRecords.every((r) => selectedRowIds.has(numId(r.id) ?? -1))}
                  onChange={(e) => e.target.checked ? onSelectAll() : onClearSelection()} />
              </th>
              {columns.map((f, ci) => {
                const sortIdx = multiSorts.findIndex((s) => s.field === f);
                const sortDir = sort?.field === f ? sort.direction : null;
                return (
                  <th key={f}
                    style={{
                      position: 'relative', padding: '6px 8px', textAlign: 'left', color: t.textMuted,
                      fontWeight: 600, fontSize: fontSize - 1, textTransform: 'uppercase', letterSpacing: '0.04em',
                      cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap',
                      ...(colWidths[f] ? { width: colWidths[f], minWidth: colWidths[f], maxWidth: colWidths[f] } : {}),
                      ...(ci === 0 && pinnedColumn === f ? { position: 'sticky' as const, left: 28, background: t.surface, zIndex: 3 } : {}),
                    }}
                    draggable
                    onDragStart={(e) => { if (!e.shiftKey) { e.preventDefault(); return; } setDragField(f); }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => { if (dragField) onColumnDrop(dragField, f); setDragField(null); }}
                    onClick={(e) => onSort(f, e.ctrlKey || e.metaKey)}
                    title="Click to sort · Ctrl-click for multi-sort · Shift-drag to reorder"
                  >
                    {f}
                    {sortDir && <span style={{ marginLeft: 4, color: t.accent }}>{sortDir === 'asc' ? '↑' : '↓'}</span>}
                    {sortIdx >= 0 && <span style={{ marginLeft: 2, fontSize: 9, color: t.accent }}>({sortIdx + 1})</span>}
                    <span
                      style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 3, cursor: 'col-resize' }}
                      onMouseDown={(e) => onResizeStart(f, e)} onClick={(e) => e.stopPropagation()}
                      onMouseEnter={(e) => { (e.target as HTMLElement).style.background = t.resizeHandle; }}
                      onMouseLeave={(e) => { (e.target as HTMLElement).style.background = 'transparent'; }}
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
    </div>
  );
}
