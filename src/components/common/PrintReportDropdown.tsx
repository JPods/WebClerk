/* LastChecked: 2026-08-06 | WhereUsed: DetailToolbar | WhoCreated: Claude */
/**
 * PrintReportDropdown — dropdown listing available print reports for a model.
 *
 * Source of truth: Report records with output_type='print' and
 * model_name matching the model key. Each Report's config may hold
 * a document_type for pdfme PDF generation.
 *
 * Reports have UUIDs — WC_HQ can push updates to fix defective templates.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { FaPrint, FaChevronDown } from "react-icons/fa";
import { getRecords } from "@/api/wcapi";

// ── Types ─────────────────────────────────────────────────────────────

export interface ReportRecord {
  id: number;
  uuid?: string;
  name: string;
  description?: string;
  model_name: string;
  output_type: string;
  category: string;
  sort_order: number;
  role_required?: string;
  config?: {
    document_type?: string;
    [key: string]: unknown;
  };
  is_active?: boolean;
}

export interface PrintReportDropdownProps {
  modelKey: string;
  onSelect?: (report: ReportRecord) => void;
  className?: string;
  compact?: boolean;
  disabled?: boolean;
}

// ── Category display ──────────────────────────────────────────────────

const CATEGORY_ORDER = ['report', 'form', 'list', 'summary', 'statement', 'letter', 'label', 'export', 'utility'] as const;

const CATEGORY_LABELS: Record<string, string> = {
  form: "Forms",
  report: "Reports",
  list: "Lists",
  summary: "Summaries",
  statement: "Statements",
  letter: "Letters",
  label: "Labels",
  export: "Exports",
  utility: "Utilities",
};

// ── Component ─────────────────────────────────────────────────────────

const PrintReportDropdown: React.FC<PrintReportDropdownProps> = ({
  modelKey,
  onSelect,
  className,
  compact = true,
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Load reports from wcapi on first open
  useEffect(() => {
    if (!open || loaded) return;
    getRecords('report', {
      model_name_filter: modelKey,
      output_type: 'print',
      is_active: true,
      limit: 200,
    }).then((result: any) => {
      const rows = result?.records || result?.results || result?.data?.records || result?.data?.results || [];
      setReports(rows.filter((r: any) => r.is_active !== false));
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, [open, loaded, modelKey]);

  // Reset cache when model changes
  useEffect(() => { setLoaded(false); setReports([]); }, [modelKey]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!btnRef.current?.contains(target) && !panelRef.current?.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

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

  // Group by category
  const grouped = new Map<string, ReportRecord[]>();
  for (const r of reports) {
    const cat = r.category || 'report';
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(r);
  }
  for (const items of grouped.values()) {
    items.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  }
  const orderedCategories = CATEGORY_ORDER.filter(c => grouped.has(c));

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
              {loaded && reports.length === 0 && (
                <div className="px-4 py-3 text-xs text-gray-400 text-center">
                  No print reports for {modelKey}
                </div>
              )}
              {!loaded && (
                <div className="px-4 py-3 text-xs text-gray-400 text-center">Loading...</div>
              )}
              {orderedCategories.map((cat, catIdx) => (
                <React.Fragment key={cat}>
                  {catIdx > 0 && (
                    <div className="my-1 border-t border-gray-200 dark:border-gray-700" />
                  )}
                  <div className="px-4 py-1.5 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                    {CATEGORY_LABELS[cat] || cat}
                  </div>
                  {grouped.get(cat)!.map((report) => (
                    <button
                      key={report.id}
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        onSelect?.(report);
                      }}
                      className="flex items-start gap-2 w-full px-4 py-1.5 text-xs text-left text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                    >
                      <span className="flex-1 leading-snug">{report.name || '(unnamed)'}</span>
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
