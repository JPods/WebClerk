/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PanelTable — shared tabular layout for panels with column headers,
 * visibility / order persistence, and a "Columns" badge that opens
 * FieldOrderDialog via useListFieldConfig.
 *
 * Usage:
 *   <PanelTable
 *     storageKey="panel:items:lines"
 *     columns={LINE_COLUMNS}
 *     data={lines}
 *     rowKey={(r) => r.id}
 *     onRowAction={(r) => handleOpen(r)}
 *   />
 */
import React, { useMemo } from "react";
import { FaSlidersH } from "react-icons/fa";
import FieldOrderDialog from "@/components/common/FieldOrderDialog";
import { useListFieldConfig } from "@/hooks/useListFieldConfig";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PanelColumnDef<T = Record<string, unknown>> {
  /** Unique column key */
  key: string;
  /** Header label */
  label: string;
  /** Render a cell */
  render: (record: T) => React.ReactNode;
  /** Start visible? (default true) */
  defaultVisible?: boolean;
  /** Extra CSS on the header cell */
  headerClassName?: string;
  /** Extra CSS on each body cell */
  cellClassName?: string;
}

export interface PanelTableProps<T = Record<string, unknown>> {
  /** localStorage persistence key */
  storageKey: string;
  /** Column definitions */
  columns: PanelColumnDef<T>[];
  /** Row data */
  data: T[];
  /** Unique key per row */
  rowKey: (record: T) => string | number;
  /** Optional row-level action (renders the external-link button) */
  onRowAction?: (record: T) => void;
  /** Compact padding */
  compact?: boolean;
  /** Currently selected row key */
  selectedKey?: string | number | null;
  /** Called when a row is clicked */
  onSelectRow?: (record: T) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PanelTable<T extends Record<string, unknown>>({
  storageKey,
  columns,
  data,
  rowKey,
  onRowAction,
  compact = false,
  selectedKey = null,
  onSelectRow,
}: PanelTableProps<T>) {
  // Column definitions as TableColumn shape for useListFieldConfig
  const tableColumns = useMemo(
    () => columns.map((c) => ({ id: c.key, name: c.label })),
    [columns],
  );

  const fc = useListFieldConfig(storageKey, tableColumns);

  // Visible columns in configured order
  const visibleColumns = useMemo(() => {
    const colMap = new Map(columns.map((c) => [c.key, c]));
    return fc.effectiveKeys
      .map((k) => colMap.get(k))
      .filter((c): c is PanelColumnDef<T> => !!c);
  }, [fc.effectiveKeys, columns]);

  const py = compact ? "py-1" : "py-1.5";

  return (
    <>
      {/* Column headers */}
      <div
        className={`flex items-center gap-3 px-3 ${py} border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60`}
      >
        {visibleColumns.map((col) => (
          <span
            key={col.key}
            className={`text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 truncate ${
              col.headerClassName ?? ""
            } ${col.cellClassName ?? ""}`}
          >
            {col.label}
          </span>
        ))}
        {/* Spacer for action column */}
        <span className="ml-auto shrink-0 flex items-center">
          <button
            type="button"
            title="Configure columns"
            className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              fc.toggleDialog();
            }}
          >
            <FaSlidersH size={10} />
          </button>
        </span>
      </div>

      {/* Data rows */}
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {data.map((record) => {
          const rk = rowKey(record);
          const isSelected = selectedKey != null && rk === selectedKey;
          return (
            <div
              key={rk}
              className={`flex items-center gap-3 text-xs cursor-pointer ${py} ${
                isSelected
                  ? 'bg-[#fff3cd] dark:bg-yellow-900/30'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
              }`}
              onClick={() => onSelectRow?.(record)}
            >
              {/* Selection indicator bar */}
              <div className={`w-1 self-stretch rounded-sm shrink-0 ${isSelected ? 'bg-blue-500' : ''}`} />
              {visibleColumns.map((col) => (
                <span
                  key={col.key}
                  className={`truncate ${col.cellClassName ?? ""}`}
                >
                  {col.render(record)}
                </span>
              ))}
              {onRowAction && (
                <span className="ml-auto shrink-0">
                  <button
                    type="button"
                    title="Open in floating window"
                    className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRowAction(record);
                    }}
                  >
                    &#8599;
                  </button>
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Column setup dialog */}
      <FieldOrderDialog {...fc.fieldOrderDialogProps} />
    </>
  );
}
