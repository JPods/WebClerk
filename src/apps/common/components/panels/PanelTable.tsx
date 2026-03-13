/**
 * PanelTable — shared tabular layout for panels with column headers,
 * visibility / order persistence, and a "Columns" badge that opens
 * ColumnSetupDialog.
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
import React, { useMemo, useState } from "react";
import { FaSlidersH } from "react-icons/fa";
import { ColumnSetupDialog } from "@/components/common/ColumnSetupDialog";
import { useColumnSetups } from "@/hooks/useColumnSetups";
import type { ColumnSetupEntry } from "@/hooks/useColumnSetups";

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
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PanelTable<T extends Record<string, unknown>>({
  storageKey,
  columns,
  data,
  rowKey,
  onRowAction,
  compact = false,
}: PanelTableProps<T>) {
  const [dialogOpen, setDialogOpen] = useState(false);

  const columnSetups = useColumnSetups(storageKey);

  // Build default config from column definitions
  const defaultConfig = useMemo<ColumnSetupEntry>(() => {
    const order = columns.map((c) => c.key);
    const visibility: Record<string, boolean> = {};
    columns.forEach((c) => {
      visibility[c.key] = c.defaultVisible !== false;
    });
    return { order, visibility, widths: {}, sort: null };
  }, [columns]);

  // Apply active setup (if any) over default
  const activeConfig = useMemo<ColumnSetupEntry>(() => {
    if (!columnSetups.activeSetupName) return defaultConfig;
    const applied = columnSetups.applySetup(columnSetups.activeSetupName);
    if (!applied) return defaultConfig;
    // Merge: use applied order/visibility but ensure new columns aren't dropped
    const knownKeys = new Set(columns.map((c) => c.key));
    const order = [
      ...applied.order.filter((k) => knownKeys.has(k)),
      ...columns.map((c) => c.key).filter((k) => !applied.order.includes(k)),
    ];
    const visibility = { ...defaultConfig.visibility, ...applied.visibility };
    return { ...applied, order, visibility };
  }, [columnSetups, defaultConfig, columns]);

  // Visible columns in configured order
  const visibleColumns = useMemo(
    () =>
      activeConfig.order
        .map((key) => columns.find((c) => c.key === key))
        .filter(
          (c): c is PanelColumnDef<T> =>
            !!c && activeConfig.visibility[c.key] !== false,
        ),
    [activeConfig, columns],
  );

  const columnMetas = useMemo(
    () => columns.map((c) => ({ key: c.key, label: c.label })),
    [columns],
  );

  const handleSave = (config: ColumnSetupEntry) => {
    columnSetups.saveSetup("current", config);
    setDialogOpen(false);
  };

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
              setDialogOpen(true);
            }}
          >
            <FaSlidersH size={10} />
          </button>
        </span>
      </div>

      {/* Data rows */}
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {data.map((record) => (
          <div
            key={rowKey(record)}
            className={`flex items-center gap-3 px-3 ${py} hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs`}
          >
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
        ))}
      </div>

      {/* Column setup dialog */}
      <ColumnSetupDialog
        open={dialogOpen}
        title={`${storageKey} — Column Setup`}
        columnMetas={columnMetas}
        config={activeConfig}
        existingSetupNames={columnSetups.setups.map((s) => s.name)}
        namedSetups={columnSetups.setups}
        initialSetupName={columnSetups.activeSetupName}
        onSaveNamed={(name, config) => columnSetups.saveSetup(name, config)}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
        columnSetupsApi={columnSetups}
      />
    </>
  );
}
