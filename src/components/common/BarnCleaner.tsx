/**
 * BarnCleaner — Alice's report approval workflow.
 *
 * Forces users to review every report that hasn't been approved.
 * For each report:
 *   1. Finds a representative record with real data
 *   2. Renders the report as a PDF preview
 *   3. User decides: Keep (with reason), Restructure (opens Designer), or Deactivate
 *   4. Report gets reviewed_by + dt_approved stamp
 *
 * Floating window — can be opened from Alice coaching, DataBrowser, or settings.
 * No report escapes without a human decision.
 *
 * Route: accessible via Alice menu or /barn-cleaner
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useAppSelector } from '@/store/hooks';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { getRecords, saveRecord } from '@/api/wcapi';

interface ReportRecord {
  id: number;
  name: string;
  description?: string;
  model_name?: string;
  category?: string;
  output_type?: string;
  config?: any;
  metadata?: any;
}

interface BarnCleanerProps {
  /** Filter to a specific model (optional — null = all models) */
  modelFilter?: string | null;
  onClose: () => void;
}

type Decision = 'keep' | 'restructure' | 'deactivate' | 'trash';

const BarnCleaner: React.FC<BarnCleanerProps> = ({ modelFilter, onClose }) => {
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [stats, setStats] = useState({ reviewed: 0, kept: 0, restructured: 0, deactivated: 0, trashed: 0 });

  // Load unapproved reports
  useEffect(() => {
    setLoading(true);
    const params: any = {
      filters: JSON.stringify({
        ...(modelFilter ? { model_name: modelFilter } : {}),
        is_active: true,
        is_deleted: false,
      }),
      limit: 500,
    };

    getRecords('report', params).then((result: any) => {
      const rows: ReportRecord[] = result?.results || result?.records || [];
      // Filter to unapproved: no metadata.flow.dt_approved
      const unapproved = rows.filter((r) => {
        const flow = r.metadata?.flow || {};
        return !flow.dt_approved;
      });
      setReports(unapproved);
      setCurrentIndex(0);
      if (unapproved.length > 0) {
        loadPreview(unapproved[0]);
      }
    }).catch(() => {
      setReports([]);
    }).finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelFilter]);

  // Load PDF preview for a report using a representative record
  const loadPreview = useCallback(async (report: ReportRecord) => {
    setPreviewLoading(true);
    setPreviewUrl(null);

    if (!report.model_name || report.output_type !== 'print') {
      setPreviewLoading(false);
      return;
    }

    try {
      // Find a representative record — prefer one with lines and totals
      const recordsRes: any = await getRecords(report.model_name, { limit: 5 });
      const records = recordsRes?.results || recordsRes?.records || [];

      // Pick the best representative: has total > 0, or first available
      const representative = records.find((r: any) =>
        r.total && parseFloat(r.total) > 0
      ) || records[0];

      if (!representative) {
        setPreviewLoading(false);
        return;
      }

      // Generate preview URL via the server endpoint
      const reportName = encodeURIComponent(report.name);
      const modelName = encodeURIComponent(report.model_name);
      const url = `/wcapi/report/?report=${reportName}&model=${modelName}&id=${representative.id}&format=html`;
      setPreviewUrl(url);
    } catch {
      // No preview available
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  const currentReport = reports[currentIndex] || null;
  const total = reports.length;
  const remaining = total - currentIndex;

  // Handle decision
  const handleDecision = async (decision: Decision) => {
    if (!currentReport) return;
    setSaving(true);

    const now = new Date().toISOString();
    const userId = user?.id || 0;
    const userName = user ? `${user.name_first || ''} ${user.name_last || ''}`.trim() : 'Unknown';

    try {
      const meta = currentReport.metadata || {};
      const flow = meta.flow || {};

      if (decision === 'trash') {
        // Hard delete — is_deleted=true, gone from all queries
        await saveRecord('report', {
          id: currentReport.id,
          is_active: false,
          is_deleted: true,
          metadata: {
            ...meta,
            flow: {
              ...flow,
              dt_approved: now,
              reviewed_by: userId,
              reviewed_by_name: userName,
              review_decision: 'trashed',
              review_reason: reason || 'Trashed during barn cleaning — no value',
            },
          },
        });
        setStats((s) => ({ ...s, reviewed: s.reviewed + 1, trashed: s.trashed + 1 }));
        dispatch(showToast({ message: `"${currentReport.name}" trashed`, type: 'info' }));

      } else if (decision === 'deactivate') {
        // Soft deactivate — still recoverable, just hidden from lists
        await saveRecord('report', {
          id: currentReport.id,
          is_active: false,
          metadata: {
            ...meta,
            flow: {
              ...flow,
              dt_approved: now,
              reviewed_by: userId,
              reviewed_by_name: userName,
              review_decision: 'deactivated',
              review_reason: reason || 'Deactivated during barn cleaning — not needed now',
            },
          },
        });
        setStats((s) => ({ ...s, reviewed: s.reviewed + 1, deactivated: s.deactivated + 1 }));
        dispatch(showToast({ message: `"${currentReport.name}" deactivated`, type: 'info' }));

      } else if (decision === 'keep') {
        if (!reason.trim()) {
          dispatch(showToast({ message: 'Explain why this report is worth keeping', type: 'error' }));
          setSaving(false);
          return;
        }
        // Approve the report
        await saveRecord('report', {
          id: currentReport.id,
          metadata: {
            ...meta,
            flow: {
              ...flow,
              dt_approved: now,
              reviewed_by: userId,
              reviewed_by_name: userName,
              review_decision: 'kept',
              review_reason: reason,
            },
          },
        });
        setStats((s) => ({ ...s, reviewed: s.reviewed + 1, kept: s.kept + 1 }));
        dispatch(showToast({ message: `"${currentReport.name}" approved`, type: 'success' }));

      } else if (decision === 'restructure') {
        // Mark as needing restructure, then open Designer
        await saveRecord('report', {
          id: currentReport.id,
          metadata: {
            ...meta,
            flow: {
              ...flow,
              dt_approved: now,
              reviewed_by: userId,
              reviewed_by_name: userName,
              review_decision: 'restructure',
              review_reason: reason || 'Needs redesign in PDF Designer',
            },
          },
        });
        setStats((s) => ({ ...s, reviewed: s.reviewed + 1, restructured: s.restructured + 1 }));
        // Open PDF Designer in new tab with this report ID
        window.open(`/pdf-designer/${currentReport.id}`, '_blank');
        dispatch(showToast({ message: `"${currentReport.name}" — opened in Designer`, type: 'info' }));
      }

      // Advance to next report
      setReason('');
      const nextIndex = currentIndex + 1;
      if (nextIndex < reports.length) {
        setCurrentIndex(nextIndex);
        loadPreview(reports[nextIndex]);
      }
    } catch (err: any) {
      dispatch(showToast({ message: err?.message || 'Save failed', type: 'error' }));
    } finally {
      setSaving(false);
    }
  };

  // Skip (come back later)
  const handleSkip = () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex < reports.length) {
      setCurrentIndex(nextIndex);
      setReason('');
      loadPreview(reports[nextIndex]);
    }
  };

  // ── Loading state ──
  if (loading) {
    return (
      <div style={floatingStyle}>
        <div style={{ padding: 40, textAlign: 'center', color: '#aaa' }}>
          <div style={{ fontSize: 18, marginBottom: 8 }}>Alice is gathering reports...</div>
        </div>
      </div>
    );
  }

  // ── All done ──
  if (!currentReport || currentIndex >= reports.length) {
    return (
      <div style={floatingStyle}>
        <div style={{ padding: 40, textAlign: 'center' }}>
          <div style={{ fontSize: 24, marginBottom: 16 }}>
            {total === 0 ? '✅ All reports are approved' : '✅ Barn cleaning complete'}
          </div>
          <div style={{ fontSize: 14, color: '#aaa', marginBottom: 24 }}>
            {stats.reviewed > 0 && (
              <>
                Reviewed: {stats.reviewed} &nbsp;|&nbsp;
                Kept: {stats.kept} &nbsp;|&nbsp;
                Restructured: {stats.restructured} &nbsp;|&nbsp;
                Deactivated: {stats.deactivated} &nbsp;|&nbsp;
                Trashed: {stats.trashed}
              </>
            )}
          </div>
          <button onClick={onClose} style={btnStyle('#3b82f6')}>Close</button>
        </div>
      </div>
    );
  }

  const usage = currentReport.metadata?.flow || {};
  const useCount = usage.use_count || 0;
  const userCount = (usage.used_by || []).length;

  return (
    <div style={floatingStyle}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 16px', borderBottom: '1px solid #333',
        background: '#1e1e2e',
      }}>
        <div>
          <span style={{ fontSize: 16, fontWeight: 700, color: '#e0e0e0' }}>
            🧹 Clean the Barn
          </span>
          <span style={{ fontSize: 12, color: '#888', marginLeft: 12 }}>
            {currentIndex + 1} of {total} &nbsp;({remaining} remaining)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => window.open('/library/reports', '_blank')}
            style={{ ...btnStyle('#6366f1'), fontSize: 12, padding: '5px 10px' }}
            title="Browse the WebClerk library for tested report templates"
          >
            📚 WCHQ Library
          </button>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#888',
            fontSize: 20, cursor: 'pointer',
          }}>&times;</button>
        </div>
      </div>

      {/* Alice coaching banner — shown on first report */}
      {currentIndex === 0 && (
        <div style={{
          padding: '10px 16px', background: '#1a2744', borderBottom: '1px solid #333',
          fontSize: 12, color: '#93c5fd', lineHeight: 1.5,
        }}>
          <strong>Alice:</strong> Weed aggressively. It is better to trash something and recover it later
          than to wade through clutter every day. If you trash a report you need,
          browse the <strong>WCHQ Library</strong> or ask me — I can restore anything.
          The cost of clutter is paid daily. The cost of recovery is paid once.
          A clean barn with six excellent reports beats a cluttered barn with sixty mediocre ones.
        </div>
      )}

      {/* Report info */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #333' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 600, color: '#e0e0e0' }}>
              {currentReport.name}
            </div>
            <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
              {currentReport.model_name} &nbsp;|&nbsp; {currentReport.category || 'uncategorized'}
              &nbsp;|&nbsp; {currentReport.output_type || 'print'}
            </div>
            {currentReport.description && (
              <div style={{ fontSize: 13, color: '#ccc', marginTop: 6 }}>
                {currentReport.description}
              </div>
            )}
          </div>
          <div style={{ textAlign: 'right', fontSize: 12, color: '#aaa' }}>
            <div>Used: <strong style={{ color: useCount > 0 ? '#4ade80' : '#ef4444' }}>{useCount}x</strong></div>
            <div>Users: {userCount}</div>
            {usage.last_used_utc && <div>Last: {usage.last_used_utc.split('T')[0]}</div>}
          </div>
        </div>
      </div>

      {/* Preview area */}
      <div style={{ flex: 1, overflow: 'hidden', background: '#111', position: 'relative' }}>
        {previewLoading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
            Loading preview...
          </div>
        )}
        {previewUrl ? (
          <iframe
            src={previewUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Report Preview"
          />
        ) : !previewLoading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666' }}>
            {currentReport.output_type !== 'print'
              ? `This is a ${currentReport.output_type} report — no PDF preview available`
              : 'No representative data available for preview'}
          </div>
        )}
      </div>

      {/* Decision area */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #333', background: '#1e1e2e' }}>
        {/* Reason input */}
        <div style={{ marginBottom: 10 }}>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={`Why keep this report? (required for Keep)`}
            style={{
              width: '100%', padding: '8px 12px', fontSize: 13,
              border: '1px solid #444', borderRadius: 4,
              background: '#2a2a3a', color: '#e0e0e0',
              outline: 'none',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && reason.trim()) handleDecision('keep');
            }}
          />
        </div>

        {/* Decision buttons */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => handleDecision('trash')}
              disabled={saving}
              style={btnStyle('#7f1d1d')}
              title="Permanent trash — this report has no value"
            >
              🗑 Trash
            </button>
            <button
              onClick={() => handleDecision('deactivate')}
              disabled={saving}
              style={btnStyle('#ef4444')}
              title="Deactivate — hidden but recoverable"
            >
              ✕ Deactivate
            </button>
            <button
              onClick={() => handleDecision('restructure')}
              disabled={saving}
              style={btnStyle('#f59e0b')}
              title="Open in PDF Designer to redesign"
            >
              ✏️ Restructure
            </button>
            <button
              onClick={() => handleDecision('keep')}
              disabled={saving || !reason.trim()}
              style={{
                ...btnStyle('#22c55e'),
                opacity: reason.trim() ? 1 : 0.4,
                cursor: reason.trim() ? 'pointer' : 'not-allowed',
              }}
              title="Approve this report — requires a reason"
            >
              ✓ Keep
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => window.open(
                `/library/reports?model=${currentReport?.model_name || ''}`,
                '_blank'
              )}
              style={{ ...btnStyle('#6366f1'), fontSize: 12 }}
              title="Browse WCHQ library for a better version of this report"
            >
              📚 Library
            </button>
            <button
              onClick={handleSkip}
              disabled={saving}
              style={btnStyle('#555')}
              title="Skip — come back later"
            >
              Skip →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Styles ──

const floatingStyle: React.CSSProperties = {
  position: 'fixed',
  top: '5%', left: '10%',
  width: '80%', height: '85%',
  zIndex: 10000,
  background: '#1a1a2e',
  border: '1px solid #333',
  borderRadius: 8,
  boxShadow: '0 12px 48px rgba(0,0,0,0.6)',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  color: '#e0e0e0',
};

const btnStyle = (bg: string): React.CSSProperties => ({
  padding: '8px 16px',
  fontSize: 13,
  fontWeight: 600,
  border: 'none',
  borderRadius: 4,
  background: bg,
  color: '#fff',
  cursor: 'pointer',
});

export default BarnCleaner;
