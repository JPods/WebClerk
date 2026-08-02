/**
 * ReportsDialog — Reports selector.
 *
 * WC2 behavior:
 *   - Cmd+P           → print primary report (sort_order 0, no dialog)
 *   - Print button / Cmd+Opt+P → open this dialog
 *   - Double-click row → execute that report
 *   - Report Setup     → open report for editing (authority-gated)
 *   - New Report       → create a new report (authority-gated)
 *
 * Data source: getRecords('report', { model_name }) filtered client-side
 *
 * LastChecked: 2026-07-21 | WhereUsed: AdminWorkbench, TransactionDetailBase | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ReportRecord {
  id: number;
  name: string;
  model_name?: string;
  category?: string;
  output_type?: string;
  description?: string;
  sort_order?: number;
  report_type?: 'list' | 'record' | string;
  format?: string;
  config?: Record<string, unknown>;
}

interface Props {
  open: boolean;
  model: string;
  context: 'list' | 'detail';
  /** Selected record ID for detail-context reports */
  selectedId: number | null;
  theme: {
    bg: string; surface: string; surfaceAlt: string;
    border: string; borderLight: string;
    text: string; textMuted: string; textDim: string;
    accent: string; accentGreen: string; accentGold: string; accentRed: string; accentPurple: string;
    [k: string]: string;
  };
  fontSize: number;
  onClose: () => void;
  /** Called when user double-clicks a report row — executes the report.
   *  If not provided, default: opens /wcapi/report/ in new tab. */
  onExecuteReport?: (report: ReportRecord) => void;
  /** Whether user has edit authority on reports (default true) */
  canEditReports?: boolean;
  /** Whether user has create authority on reports (default true) */
  canCreateReports?: boolean;
}

// ---------------------------------------------------------------------------
// Output type display
// ---------------------------------------------------------------------------

const OUTPUT_TYPE_LABELS: Record<string, { label: string; icon: string }> = {
  print:  { label: 'Print',  icon: '🖨️' },
  email:  { label: 'Email',  icon: '✉️' },
  export: { label: 'Export', icon: '📤' },
  label:  { label: 'Label',  icon: '🏷️' },
  letter: { label: 'Letter', icon: '📝' },
  list:   { label: 'List',   icon: '📋' },
  api:    { label: 'API',    icon: '🔗' },
  json:   { label: 'JSON',   icon: '{ }' },
  merge:  { label: 'Merge',  icon: '📎' },
};

// ---------------------------------------------------------------------------
// Category badge colors
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  report:     '#0e639c',
  financial:  '#0e639c',
  statement:  '#1a6b2e',
  inventory:  '#1a6b2e',
  list:       '#6f42c1',
  operational:'#6f42c1',
  summary:    '#fd7e14',
  customer:   '#fd7e14',
  letter:     '#2c8c99',
  label:      '#9c6b0e',
  export:     '#666',
  utility:    '#555',
  default:    '#555',
};

function categoryColor(cat?: string): string {
  if (!cat) return CATEGORY_COLORS.default;
  return CATEGORY_COLORS[cat.toLowerCase()] || CATEGORY_COLORS.default;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ReportsDialog: React.FC<Props> = ({
  open, model, context, selectedId,
  theme: t, fontSize, onClose,
  onExecuteReport,
  canEditReports = true,
  canCreateReports = true,
}) => {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedModel, setLoadedModel] = useState('');
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const listRef = useRef<HTMLDivElement>(null);

  // ---- Fetch reports for this model ----
  useEffect(() => {
    if (!open || !model || loadedModel === model) return;
    setLoading(true);
    getRecords('report', { model_name: model }).then((result: any) => {
      const rows: ReportRecord[] = result?.results || result?.records || result?.data?.results || result?.data?.records || [];
      // Sort: sort_order asc, then name
      rows.sort((a, b) => {
        const sa = a.sort_order ?? 999;
        const sb = b.sort_order ?? 999;
        if (sa !== sb) return sa - sb;
        return (a.name || '').localeCompare(b.name || '');
      });
      setReports(rows);
      setLoadedModel(model);
      setSelectedIndex(rows.length > 0 ? 0 : -1);
    }).catch(() => {
      setReports([]);
      setLoadedModel(model);
    }).finally(() => setLoading(false));
  }, [open, model, loadedModel]);

  // Reset when model changes
  useEffect(() => { setLoadedModel(''); }, [model]);

  // ---- Filter by context ----
  const filteredReports = reports.filter((r) => {
    const rt = (r.report_type || '').toLowerCase();
    const cat = (r.category || '').toLowerCase();
    // Tools (dedup, normalize, etc.) show in both contexts
    if (cat === 'tool') return true;
    if (context === 'list') return rt === 'list' || cat === 'list' || cat === 'summary' || cat === 'export';
    return rt !== 'list'; // detail shows everything except list-only
  });

  // ---- Keyboard: Escape, Enter, Arrow keys ----
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, filteredReports.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' && selectedIndex >= 0 && selectedIndex < filteredReports.length) {
        e.preventDefault();
        executeReport(filteredReports[selectedIndex]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose, selectedIndex, filteredReports.length]);

  // Scroll selected row into view
  useEffect(() => {
    if (selectedIndex < 0 || !listRef.current) return;
    const rows = listRef.current.querySelectorAll('[data-wc="reports-dialog-row"]');
    rows[selectedIndex]?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  // ---- Execute report (double-click or Enter) ----
  const executeReport = useCallback((report: ReportRecord) => {
    if (onExecuteReport) {
      onExecuteReport(report);
      onClose();
      return;
    }
    // Default: open report endpoint in new tab
    const reportName = encodeURIComponent(report.name);
    const modelName = encodeURIComponent(model);
    let url = `/wcapi/report/?report=${reportName}&model=${modelName}`;
    if (context === 'detail' && selectedId) {
      url += `&id=${selectedId}`;
    }
    window.open(url, '_blank');
    onClose();
  }, [onExecuteReport, model, context, selectedId, onClose]);

  // ---- Report Setup: open in PDF Designer ----
  const handleSetup = useCallback((report: ReportRecord) => {
    let url = `/pdf-designer/${report.id}`;
    if (context === 'detail' && selectedId) {
      url += `?preview_model=${model}&preview_id=${selectedId}`;
    }
    window.open(url, '_blank');
  }, [context, selectedId, model]);

  // ---- New Report ----
  const handleNewReport = useCallback(() => {
    let url = `/pdf-designer?model=${encodeURIComponent(model)}`;
    window.open(url, '_blank');
  }, [model]);

  if (!open) return null;

  const isPrimary = (r: ReportRecord) => (r.sort_order ?? 999) === 0;

  return (
    // Backdrop
    <div data-wc="reports-dialog-backdrop"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
      {/* Dialog */}
      <div data-wc="reports-dialog"
        style={{
          background: t.surface, border: `1px solid ${t.border}`,
          borderRadius: 8, width: 620, maxHeight: '75vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>

        {/* Header */}
        <div style={{
          padding: '12px 16px', borderBottom: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: fontSize + 2, color: t.accent }}>
              Reports
            </span>
            <span style={{ fontSize: fontSize - 1, color: t.textMuted, marginLeft: 8 }}>
              {model}
            </span>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: t.textMuted,
            fontSize: 18, cursor: 'pointer', padding: '0 4px',
          }}>&times;</button>
        </div>

        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: '70px 1fr 72px 28px',
          gap: 8, padding: '6px 16px',
          borderBottom: `1px solid ${t.borderLight}`,
          fontSize: fontSize - 2, fontWeight: 700, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: '0.05em',
        }}>
          <span>Type</span>
          <span>Report Name</span>
          <span style={{ textAlign: 'center' }}>Output</span>
          <span></span>
        </div>

        {/* Body — report list */}
        <div ref={listRef} style={{ flex: 1, overflowY: 'auto', padding: '4px 0', minHeight: 120 }}>
          {loading && (
            <div style={{ padding: '16px', color: t.textMuted, textAlign: 'center' }}>
              Loading...
            </div>
          )}
          {!loading && filteredReports.length === 0 && (
            <div style={{ padding: '24px 16px', color: t.textDim, textAlign: 'center' }}>
              No reports configured for {model}
            </div>
          )}
          {!loading && filteredReports.map((report, i) => {
            const isSelected = i === selectedIndex;
            const primary = isPrimary(report);
            const ot = OUTPUT_TYPE_LABELS[report.output_type || 'print'] || OUTPUT_TYPE_LABELS.print;

            return (
              <div key={report.id}
                data-wc="reports-dialog-row"
                onClick={() => setSelectedIndex(i)}
                onDoubleClick={() => executeReport(report)}
                style={{
                  display: 'grid', gridTemplateColumns: '70px 1fr 72px 28px',
                  gap: 8, alignItems: 'center',
                  padding: '8px 16px', cursor: 'pointer',
                  borderBottom: i < filteredReports.length - 1 ? `1px solid ${t.borderLight}` : 'none',
                  background: isSelected ? t.surfaceAlt : 'transparent',
                  borderLeft: primary ? `3px solid ${t.accent}` : '3px solid transparent',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = t.surfaceAlt;
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                {/* Category badge */}
                <span style={{
                  padding: '2px 6px', borderRadius: 3, fontSize: fontSize - 3,
                  fontWeight: 700, background: categoryColor(report.category), color: '#fff',
                  textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>{report.category || 'report'}</span>

                {/* Name + description */}
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontWeight: 600, color: t.text, fontSize }}>
                      {report.name}
                    </span>
                    {primary && (
                      <span style={{
                        fontSize: fontSize - 3, padding: '1px 5px', borderRadius: 3,
                        background: t.accent, color: '#fff', fontWeight: 700,
                      }}>PRIMARY</span>
                    )}
                  </div>
                  {report.description && (
                    <div style={{
                      fontSize: fontSize - 2, color: t.textMuted, marginTop: 1,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>{report.description}</div>
                  )}
                </div>

                {/* Output type */}
                <span style={{
                  fontSize: fontSize - 2, color: t.textDim, textAlign: 'center',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 3,
                }}>
                  <span>{ot.icon}</span>
                  <span>{ot.label}</span>
                </span>

                {/* Per-row edit button */}
                {canEditReports ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleSetup(report); }}
                    title="Report Setup"
                    style={{
                      background: 'none', border: `1px solid ${t.borderLight}`,
                      borderRadius: 3, padding: '1px 4px', cursor: 'pointer',
                      fontSize: fontSize - 2, color: t.textMuted, lineHeight: 1,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = t.accent;
                      (e.currentTarget as HTMLElement).style.color = t.accent;
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = t.borderLight;
                      (e.currentTarget as HTMLElement).style.color = t.textMuted;
                    }}
                  >&#9998;</button>
                ) : <span />}
              </div>
            );
          })}
        </div>

        {/* Footer — WC2: Report Setup + New Setup buttons */}
        <div style={{
          padding: '10px 16px', borderTop: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            {context === 'detail' && selectedId
              ? `Record #${selectedId}`
              : 'List reports'}
            {' · Double-click to print · '}
            <span style={{ color: t.textDim }}>
              {navigator.platform.includes('Mac') ? '⌘P' : 'Ctrl+P'} = Primary
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {canEditReports && selectedIndex >= 0 && selectedIndex < filteredReports.length && (
              <button
                onClick={() => handleSetup(filteredReports[selectedIndex])}
                style={{
                  padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
                  fontSize: fontSize - 1, fontWeight: 600,
                  background: 'none', border: `1px solid ${t.border}`,
                  color: t.text,
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
              >
                Report Setup
              </button>
            )}
            {canCreateReports && (
              <button
                onClick={handleNewReport}
                style={{
                  padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
                  fontSize: fontSize - 1, fontWeight: 600,
                  background: t.accent, border: 'none', color: '#fff',
                }}
              >
                New Report
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsDialog;
export type { Props as ReportsDialogProps };
