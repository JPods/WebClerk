/**
 * ColumnSetupDialog – modal for viewing / editing a named column-setup configuration.
 *
 * Shows a table of columns with toggles for visibility, editable width fields,
 * drag-to-reorder rows, and sort selection.
 */

import { useCallback, useEffect, useState } from "react";
import type { ColumnSetupEntry, ColumnSort } from "@/hooks/useColumnSetups";

// ── Props ─────────────────────────────────────────────────────────────────────

interface ColumnMeta {
  /** Persist-key used in the setup (matches getColumnPersistKey output) */
  key: string;
  /** Human label for the column */
  label: string;
}

export interface ColumnSetupDialogProps {
  open: boolean;
  /** display title */
  title: string;
  /** Column metadata (key + label) in their *original* definition order */
  columnMetas: ColumnMeta[];
  /** The config being viewed / edited */
  config: ColumnSetupEntry;
  onClose: () => void;
  onSave: (config: ColumnSetupEntry) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export const ColumnSetupDialog = ({
  open,
  title,
  columnMetas,
  config,
  onClose,
  onSave,
}: ColumnSetupDialogProps) => {
  // Local edit state
  const [order, setOrder] = useState<string[]>([]);
  const [visibility, setVisibility] = useState<Record<string, boolean>>({});
  const [widths, setWidths] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<ColumnSort | null>(null);

  // Hydrate from config when dialog opens
  useEffect(() => {
    if (!open) return;
    // Build order: start from config.order, then add any missing keys
    const allKeys = columnMetas.map((m) => m.key);
    const existing = new Set(config.order.filter((k) => allKeys.includes(k)));
    const ordered = [
      ...config.order.filter((k) => existing.has(k)),
      ...allKeys.filter((k) => !existing.has(k)),
    ];
    setOrder(ordered);
    setVisibility({ ...config.visibility });
    setWidths({ ...config.widths });
    setSort(config.sort ?? null);
  }, [open, config, columnMetas]);

  const labelFor = useCallback(
    (key: string) => columnMetas.find((m) => m.key === key)?.label ?? key,
    [columnMetas],
  );

  const moveItem = (index: number, direction: "up" | "down") => {
    setOrder((prev) => {
      const next = [...prev];
      const target = direction === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const handleSave = () => {
    onSave({ order, visibility, widths, sort });
    onClose();
  };

  if (!open) return null;

  const sortableKeys = order.filter((k) => visibility[k] !== false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-2xl dark:bg-slate-900 flex flex-col max-h-[85vh]">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Edit Column Setup
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Sort selector */}
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Default Sort
            </label>
            <div className="flex items-center gap-2">
              <select
                value={sort?.field ?? ""}
                onChange={(e) => {
                  const field = e.target.value;
                  if (!field) {
                    setSort(null);
                  } else {
                    setSort({ field, direction: sort?.direction ?? "asc" });
                  }
                }}
                className="flex-1 text-xs px-2 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
              >
                <option value="">None</option>
                {sortableKeys.map((key) => (
                  <option key={key} value={key}>
                    {labelFor(key)}
                  </option>
                ))}
              </select>
              {sort && (
                <button
                  type="button"
                  onClick={() =>
                    setSort({
                      ...sort,
                      direction: sort.direction === "asc" ? "desc" : "asc",
                    })
                  }
                  className="px-2 py-1.5 text-xs rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  {sort.direction === "asc" ? "↑ Asc" : "↓ Desc"}
                </button>
              )}
            </div>
          </div>

          {/* Column list */}
          <div>
            <h3 className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">
              Columns
            </h3>
            <div className="border border-slate-200 dark:border-slate-700 rounded-md divide-y divide-slate-200 dark:divide-slate-700">
              {order.map((key, index) => {
                const isVisible = visibility[key] !== false;
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-2 px-3 py-2 text-sm ${
                      isVisible ? "" : "opacity-50"
                    }`}
                  >
                    {/* Reorder buttons */}
                    <div className="flex flex-col gap-0.5">
                      <button
                        type="button"
                        disabled={index === 0}
                        onClick={() => moveItem(index, "up")}
                        className="text-[10px] leading-none text-slate-400 hover:text-slate-700 disabled:opacity-30 dark:hover:text-slate-200"
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        disabled={index === order.length - 1}
                        onClick={() => moveItem(index, "down")}
                        className="text-[10px] leading-none text-slate-400 hover:text-slate-700 disabled:opacity-30 dark:hover:text-slate-200"
                      >
                        ▼
                      </button>
                    </div>

                    {/* Visibility toggle */}
                    <button
                      type="button"
                      onClick={() =>
                        setVisibility((prev) => ({
                          ...prev,
                          [key]: !isVisible,
                        }))
                      }
                      className={`w-5 h-5 flex items-center justify-center rounded text-xs ${
                        isVisible
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                          : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                      }`}
                      title={isVisible ? "Hide" : "Show"}
                    >
                      {isVisible ? "👁" : "—"}
                    </button>

                    {/* Column name */}
                    <span className="flex-1 font-medium text-slate-800 dark:text-slate-200 truncate">
                      {labelFor(key)}
                    </span>

                    {/* Width input */}
                    <input
                      type="text"
                      value={widths[key] ?? ""}
                      onChange={(e) =>
                        setWidths((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      placeholder="auto"
                      className="w-20 text-xs px-1.5 py-1 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-right"
                      title="Width (e.g. 120px, 15%)"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4 dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-700"
          >
            Save
          </button>
        </footer>
      </div>
    </div>
  );
};
