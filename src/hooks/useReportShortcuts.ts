/**
 * useReportShortcuts — WC2-heritage keyboard shortcuts for printing.
 *
 *   Cmd+P       → execute the primary report (sort_order === 0) — no dialog
 *   Cmd+Opt+P   → open the Report Selector dialog
 *
 * The hook fetches available reports for the model on mount and caches them.
 * It intercepts the browser's native Cmd+P (print page) and replaces it
 * with the WC2 "print primary report" behavior.
 *
 * LastChecked: 2026-07-19 | WhereUsed: TransactionDetailBase, AdminWorkbench | WhoCreated: Bill+Claude
 */
import { useEffect, useCallback, useRef, useState } from 'react';
import { getRecords } from '@/api/wcapi';

interface ReportRecord {
  id: number;
  name: string;
  model_name?: string;
  category?: string;
  output_type?: string;
  sort_order?: number;
  config?: Record<string, unknown>;
}

interface UseReportShortcutsOptions {
  /** The model name to fetch reports for (e.g., 'invoice', 'order') */
  model: string;
  /** Whether the hook is active (e.g., only when the component is mounted and visible) */
  enabled?: boolean;
  /** Called when Cmd+P fires — execute the primary report */
  onPrintPrimary: (report: ReportRecord) => void;
  /** Called when Cmd+Opt+P fires — open the report selector */
  onOpenSelector: () => void;
}

export function useReportShortcuts({
  model,
  enabled = true,
  onPrintPrimary,
  onOpenSelector,
}: UseReportShortcutsOptions) {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const reportsRef = useRef<ReportRecord[]>([]);

  // Keep ref in sync for use in event handler
  useEffect(() => { reportsRef.current = reports; }, [reports]);

  // Fetch reports for this model
  useEffect(() => {
    if (!enabled || !model) return;
    setLoaded(false);
    getRecords('report', { limit: 500 }).then((result: any) => {
      const rows = result?.results || result?.records || result?.data?.results || result?.data?.records || [];
      const filtered = rows.filter((r: any) => {
        const rm = (r.model_name || '').toLowerCase();
        return rm === model.toLowerCase();
      });
      filtered.sort((a: ReportRecord, b: ReportRecord) => {
        const sa = a.sort_order ?? 999;
        const sb = b.sort_order ?? 999;
        if (sa !== sb) return sa - sb;
        return (a.name || '').localeCompare(b.name || '');
      });
      setReports(filtered);
      setLoaded(true);
    }).catch(() => {
      setReports([]);
      setLoaded(true);
    });
  }, [enabled, model]);

  // Keyboard handler
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!enabled) return;
    const isMac = navigator.platform.includes('Mac');
    const mod = isMac ? e.metaKey : e.ctrlKey;

    if (mod && e.key.toLowerCase() === 'p') {
      e.preventDefault();
      e.stopPropagation();

      if (e.altKey) {
        // Cmd+Opt+P → open selector
        onOpenSelector();
      } else {
        // Cmd+P → print primary (sort_order === 0)
        const primary = reportsRef.current.find(r => (r.sort_order ?? 999) === 0);
        if (primary) {
          onPrintPrimary(primary);
        } else {
          // No primary designated → open selector so user can choose
          onOpenSelector();
        }
      }
    }
  }, [enabled, onPrintPrimary, onOpenSelector]);

  useEffect(() => {
    if (!enabled) return;
    // Use capture phase to intercept before browser print dialog
    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [enabled, handleKeyDown]);

  return {
    reports,
    loaded,
    primaryReport: reports.find(r => (r.sort_order ?? 999) === 0) || reports[0] || null,
  };
}
