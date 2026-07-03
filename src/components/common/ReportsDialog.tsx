/**
 * ReportsDialog — shows available reports for the current DataBrowser model.
 *
 * Data source: getRecords('report', { model_name: currentModel })
 *
 * Two contexts:
 *   - List: shows list-type reports (aging, valuation, etc.)
 *   - Detail: shows record-type reports (invoice PDF, pick list, etc.)
 *
 * Clicking a report opens the report endpoint in a new tab.
 *
 * LastChecked: 2026-06-30 | WhereUsed: AdminWorkbench | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReportRecord {
  id: number;
  name: string;
  model_name?: string;
  category?: string;
  description?: string;
  report_type?: 'list' | 'record' | string;
  format?: string;
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
}

// ---------------------------------------------------------------------------
// Category badge colors
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  financial: '#0e639c',
  inventory: '#1a6b2e',
  operational: '#6f42c1',
  customer: '#fd7e14',
  default: '#555',
};

function categoryColor(cat?: string): string {
  if (!cat) return CATEGORY_COLORS.default;
  return CATEGORY_COLORS[cat.toLowerCase()] || CATEGORY_COLORS.default;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ReportsDialog: React.FC<Props> = ({ open, model, context, selectedId, theme: t, fontSize, onClose }) => {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedModel, setLoadedModel] = useState('');

  // Fetch reports for this model
  useEffect(() => {
    if (!open || !model || loadedModel === model) return;
    setLoading(true);
    getRecords('report', { model_name: model }).then((result: any) => {
      const rows = result?.results || result?.records || result?.data?.results || result?.data?.records || [];
      setReports(rows);
      setLoadedModel(model);
    }).catch(() => {
      setReports([]);
      setLoadedModel(model);
    }).finally(() => setLoading(false));
  }, [open, model, loadedModel]);

  // Reset when model changes
  useEffect(() => { setLoadedModel(''); }, [model]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  // Filter reports by context
  const filteredReports = reports.filter((r) => {
    const rt = (r.report_type || '').toLowerCase();
    if (context === 'list') return rt !== 'record';
    return rt !== 'list';
  });

  const handleClick = (report: ReportRecord) => {
    const reportName = encodeURIComponent(report.name);
    const modelName = encodeURIComponent(model);
    let url = `/wcapi/report/?report=${reportName}&model=${modelName}`;
    if (context === 'detail' && selectedId) {
      url += `&id=${selectedId}`;
    }
    window.open(url, '_blank');
    onClose();
  };

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
          borderRadius: 8, width: 460, maxHeight: '70vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>
        {/* Header */}
        <div style={{
          padding: '12px 16px', borderBottom: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontWeight: 700, fontSize: fontSize + 1, color: t.accent }}>
            Reports &mdash; {model}
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: t.textMuted,
            fontSize: 18, cursor: 'pointer', padding: '0 4px',
          }}>&times;</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {loading && (
            <div style={{ padding: '16px', color: t.textMuted, textAlign: 'center' }}>
              Loading...
            </div>
          )}
          {!loading && filteredReports.length === 0 && (
            <div style={{ padding: '24px 16px', color: t.textDim, textAlign: 'center' }}>
              No reports configured
            </div>
          )}
          {!loading && filteredReports.map((report, i) => (
            <div key={report.id}
              data-wc="reports-dialog-row"
              onClick={() => handleClick(report)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 16px', cursor: 'pointer',
                borderBottom: i < filteredReports.length - 1 ? `1px solid ${t.borderLight}` : 'none',
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              {/* Category badge */}
              {report.category && (
                <span style={{
                  padding: '2px 8px', borderRadius: 3, fontSize: fontSize - 2,
                  fontWeight: 700, background: categoryColor(report.category), color: '#fff',
                  flexShrink: 0, minWidth: 70, textAlign: 'center',
                }}>{report.category}</span>
              )}

              {/* Name and description */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, color: t.text, fontSize }}>{report.name}</div>
                {report.description && (
                  <div style={{ fontSize: fontSize - 2, color: t.textMuted, marginTop: 2 }}>{report.description}</div>
                )}
              </div>

              {/* Format hint */}
              <span style={{
                fontSize: fontSize - 2, color: t.textDim, fontWeight: 600,
                textTransform: 'uppercase',
              }}>{report.format || 'PDF'}</span>

              {/* Arrow */}
              <span style={{ color: t.textDim, fontSize: fontSize + 2 }}>&rarr;</span>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '8px 16px', borderTop: `1px solid ${t.border}`,
          fontSize: fontSize - 2, color: t.textMuted,
        }}>
          {context === 'detail' && selectedId ? `Record #${selectedId}` : 'List reports'}
          {' '}&middot; Opens in new tab
        </div>
      </div>
    </div>
  );
};

export default ReportsDialog;
