/**
 * PrintReportDropdown — A dropdown button that lists available
 * reports/print options for a given model, sourced from reportLists.ts.
 *
 * Usage:
 *   <PrintReportDropdown modelKey="customer" onSelect={handlePrintReport} />
 *
 * When the model has no reports defined the component renders nothing,
 * leaving the parent to fall back to a plain Print button (or nothing).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { FaPrint, FaChevronDown } from "react-icons/fa";
import {
  getReportsForModel,
  type ReportDef,
  type ReportCategory,
} from "@/config/reportLists";

// ── Category display labels (sorted order) ─────────────────────────────
const CATEGORY_ORDER: ReportCategory[] = [
  "report",
  "list",
  "summary",
  "statement",
  "letter",
  "label",
  "export",
  "utility",
];

const CATEGORY_LABELS: Record<ReportCategory, string> = {
  report: "Reports",
  list: "Lists",
  summary: "Summaries",
  statement: "Statements",
  letter: "Letters",
  label: "Labels",
  export: "Exports",
  utility: "Utilities",
};

// ── Props ──────────────────────────────────────────────────────────────

/** A simple action item injected at the top of the dropdown (e.g. quick filters). */
export interface QuickFilterItem {
  key: string;
  label: string;
  /** Whether this item is currently active/selected */
  active?: boolean;
}

export interface PrintReportDropdownProps {
  /** Model key matching reportLists.ts keys (e.g. "customer", "invoice") */
  modelKey: string;
  /** Called when the user picks a report from the dropdown */
  onSelect?: (report: ReportDef) => void;
  /** Optional quick-filter items shown above the report list */
  quickFilters?: QuickFilterItem[];
  /** Called when a quick-filter item is clicked */
  onQuickFilter?: (key: string) => void;
  /** Optional CSS class override for the trigger button */
  className?: string;
  /** When true, render a compact icon-only button (default toolbar size) */
  compact?: boolean;
  /** Whether the button should be disabled  */
  disabled?: boolean;
}

// ── Component ──────────────────────────────────────────────────────────
const PrintReportDropdown: React.FC<PrintReportDropdownProps> = ({
  modelKey,
  onSelect,
  quickFilters,
  onQuickFilter,
  className,
  compact = true,
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Resolve reports for this model
  const reports = getReportsForModel(modelKey);

  // ── Close on outside click ───────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        !btnRef.current?.contains(target) &&
        !panelRef.current?.contains(target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // ── Toggle dropdown ──────────────────────────────────────────────
  const toggle = useCallback(() => {
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      const panelWidth = 280;
      let left = rect.left;
      if (left + panelWidth > window.innerWidth - 16) {
        left = window.innerWidth - panelWidth - 16;
      }
      setPosition({ top: rect.bottom + 6, left: Math.max(8, left) });
    }
    setOpen((prev) => !prev);
  }, [open]);

  // Don't render anything when no reports AND no quick filters
  if (reports.length === 0 && (!quickFilters || quickFilters.length === 0)) return null;

  // ── Group by category (preserve defined order) ───────────────────
  const grouped = new Map<ReportCategory, ReportDef[]>();
  for (const r of reports) {
    const cat = r.category;
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(r);
  }

  // Sort within each group by sort_order
  for (const items of grouped.values()) {
    items.sort((a, b) => a.sort_order - b.sort_order);
  }

  // Order the groups by CATEGORY_ORDER
  const orderedCategories = CATEGORY_ORDER.filter((c) => grouped.has(c));

  // ── Trigger button ──────────────────────────────────────────────
  const triggerCls =
    className ??
    (compact
      ? "w-9 h-9 flex items-center justify-center rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50"
      : "flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50");

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={toggle}
        disabled={disabled}
        title="Print / Reports"
        className={triggerCls}
      >
        <FaPrint className={compact ? "w-4 h-4" : "w-3.5 h-3.5"} />
        {!compact && <span>Print</span>}
        <FaChevronDown className={compact ? "w-2 h-2 ml-px" : "w-2.5 h-2.5"} />
      </button>

      {open &&
        position &&
        createPortal(
          <div
            ref={panelRef}
            className="fixed z-[9999] w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 max-h-96 overflow-y-auto"
            style={{ top: position.top, left: position.left }}
          >
            <div className="py-1">
              {/* Quick filters section */}
              {quickFilters && quickFilters.length > 0 && (
                <>
                  <div className="px-4 py-1.5 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                    Quick Views
                  </div>
                  {quickFilters.map((qf) => (
                    <button
                      key={qf.key}
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        onQuickFilter?.(qf.key);
                      }}
                      className={`flex items-center gap-2 w-full px-4 py-1.5 text-xs text-left transition-colors ${
                        qf.active
                          ? "bg-blue-50 text-blue-700 font-medium dark:bg-blue-900/30 dark:text-blue-300"
                          : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {qf.active && (
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                      )}
                      <span className="leading-snug">{qf.label}</span>
                    </button>
                  ))}
                  {orderedCategories.length > 0 && (
                    <div className="my-1 border-t border-gray-200 dark:border-gray-700" />
                  )}
                </>
              )}

              {/* Report sections */}
              {orderedCategories.map((cat, catIdx) => (
                <React.Fragment key={cat}>
                  {catIdx > 0 && (
                    <div className="my-1 border-t border-gray-200 dark:border-gray-700" />
                  )}
                  <div className="px-4 py-1.5 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                    {CATEGORY_LABELS[cat]}
                  </div>
                  {grouped.get(cat)!.map((rpt) => (
                    <button
                      key={rpt.name}
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        onSelect?.(rpt);
                      }}
                      className="flex items-start gap-2 w-full px-4 py-1.5 text-xs text-left text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                    >
                      <span className="flex-1 leading-snug">{rpt.name}</span>
                      <span className="shrink-0 mt-0.5 px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                        {rpt.output_type}
                      </span>
                    </button>
                  ))}
                </React.Fragment>
              ))}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};

export default PrintReportDropdown;
