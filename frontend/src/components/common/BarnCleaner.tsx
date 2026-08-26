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
import './BarnCleaner.css';

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
        r.totals?.total && parseFloat(r.totals.total) > 0
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

  // -- Loading state --
  if (loading) {
    return (
      <div className="bc-root">
        <div className="bc-center-message">
          <div className="bc-loading-text">Alice is gathering reports...</div>
        </div>
      </div>
    );
  }

  // -- All done --
  if (!currentReport || currentIndex >= reports.length) {
    return (
      <div className="bc-root">
        <div className="bc-center-message">
          <div className="bc-done-title">
            {total === 0 ? 'All reports are approved' : 'Barn cleaning complete'}
          </div>
          <div className="bc-done-stats">
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
          <button onClick={onClose} className="bc-btn bc-btn--close">Close</button>
        </div>
      </div>
    );
  }

  const usage = currentReport.metadata?.flow || {};
  const useCount = usage.use_count || 0;
  const userCount = (usage.used_by || []).length;

  return (
    <div className="bc-root">
      {/* Header */}
      <div className="bc-header">
        <div>
          <span className="bc-title">Clean the Barn</span>
          <span className="bc-progress">
            {currentIndex + 1} of {total} &nbsp;({remaining} remaining)
          </span>
        </div>
        <div className="bc-header-actions">
          <button
            onClick={() => window.open('/library/reports', '_blank')}
            className="bc-btn bc-btn--library bc-btn--sm"
            title="Browse the WebClerk library for tested report templates"
          >
            WCHQ Library
          </button>
          <button onClick={onClose} className="bc-close-btn">&times;</button>
        </div>
      </div>

      {/* Alice coaching banner — shown on first report */}
      {currentIndex === 0 && (
        <div className="bc-coaching">
          <strong>Alice:</strong> Weed aggressively. It is better to trash something and recover it later
          than to wade through clutter every day. If you trash a report you need,
          browse the <strong>WCHQ Library</strong> or ask me — I can restore anything.
          The cost of clutter is paid daily. The cost of recovery is paid once.
          A clean barn with six excellent reports beats a cluttered barn with sixty mediocre ones.
        </div>
      )}

      {/* Report info */}
      <div className="bc-report-info">
        <div className="bc-report-info-row">
          <div>
            <div className="bc-report-name">
              {currentReport.name}
            </div>
            <div className="bc-report-meta">
              {currentReport.model_name} &nbsp;|&nbsp; {currentReport.category || 'uncategorized'}
              &nbsp;|&nbsp; {currentReport.output_type || 'print'}
            </div>
            {currentReport.description && (
              <div className="bc-report-desc">
                {currentReport.description}
              </div>
            )}
          </div>
          <div className="bc-report-usage">
            <div>Used: <strong className={useCount > 0 ? 'bc-usage-active' : 'bc-usage-zero'}>{useCount}x</strong></div>
            <div>Users: {userCount}</div>
            {usage.last_used_utc && <div>Last: {usage.last_used_utc.split('T')[0]}</div>}
          </div>
        </div>
      </div>

      {/* Preview area */}
      <div className="bc-preview">
        {previewLoading && (
          <div className="bc-preview-loading">
            Loading preview...
          </div>
        )}
        {previewUrl ? (
          <iframe
            src={previewUrl}
            className="bc-preview-iframe"
            title="Report Preview"
          />
        ) : !previewLoading && (
          <div className="bc-preview-empty">
            {currentReport.output_type !== 'print'
              ? `This is a ${currentReport.output_type} report — no PDF preview available`
              : 'No representative data available for preview'}
          </div>
        )}
      </div>

      {/* Decision area */}
      <div className="bc-decision">
        {/* Reason input */}
        <div className="bc-reason-wrap">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={`Why keep this report? (required for Keep)`}
            className="bc-reason-input"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && reason.trim()) handleDecision('keep');
            }}
          />
        </div>

        {/* Decision buttons */}
        <div className="bc-decision-row">
          <div className="bc-decision-left">
            <button
              onClick={() => handleDecision('trash')}
              disabled={saving}
              className="bc-btn bc-btn--trash"
              title="Permanent trash — this report has no value"
            >
              Trash
            </button>
            <button
              onClick={() => handleDecision('deactivate')}
              disabled={saving}
              className="bc-btn bc-btn--deactivate"
              title="Deactivate — hidden but recoverable"
            >
              Deactivate
            </button>
            <button
              onClick={() => handleDecision('restructure')}
              disabled={saving}
              className="bc-btn bc-btn--restructure"
              title="Open in PDF Designer to redesign"
            >
              Restructure
            </button>
            <button
              onClick={() => handleDecision('keep')}
              disabled={saving || !reason.trim()}
              className={`bc-btn bc-btn--keep`}
              title="Approve this report — requires a reason"
            >
              Keep
            </button>
          </div>

          <div className="bc-decision-right">
            <button
              onClick={() => window.open(
                `/library/reports?model=${currentReport?.model_name || ''}`,
                '_blank'
              )}
              className="bc-btn bc-btn--library bc-btn--sm"
              title="Browse WCHQ library for a better version of this report"
            >
              Library
            </button>
            <button
              onClick={handleSkip}
              disabled={saving}
              className="bc-btn bc-btn--skip"
              title="Skip — come back later"
            >
              Skip
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BarnCleaner;
