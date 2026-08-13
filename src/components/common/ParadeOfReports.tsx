/**
 * ParadeOfReports — Alice-driven onboarding tool.
 *
 * Walks users through their reports with polished sample data.
 * Users select which reports to parade, then Alice (or the user)
 * steps through each one. At each stop: Keep / Modify / Don't Need
 * plus notes. Feedback saves to the Report record via wcapi.
 *
 * Can be launched from:
 *   - ReportsDialog (onboarding button)
 *   - Alice via Chrome DevTools MCP
 *   - Direct URL: /parade
 *
 * LastChecked: 2026-08-12 | WhereUsed: ReportsDialog, Router | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { manageAction, saveRecord } from '@/api/wcapi';
import './ParadeOfReports.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ParadeReport {
  id: number;
  name: string;
  model_name: string;
  category: string;
  description: string;
  has_sample_data: boolean;
  render_url: string | null;
  feedback: ParadeFeedback | null;
}

interface ParadeGroup {
  name: string;
  description: string;
  reports: ParadeReport[];
  count: number;
}

interface ParadeManifest {
  groups: ParadeGroup[];
  total_reports: number;
  sample_models: string[];
  feedback_options: string[];
  instructions: string;
}

interface ParadeFeedback {
  decision: 'Keep' | 'Modify' | "Don't Need" | null;
  notes: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  fontSize: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map a feedback decision to the CSS modifier class suffix */
function badgeClass(decision: string | null): string {
  if (decision === 'Keep') return 'por-badge--keep';
  if (decision === 'Modify') return 'por-badge--modify';
  if (decision === "Don't Need") return 'por-badge--dont-need';
  return '';
}

function feedbackBtnClass(opt: string): string {
  if (opt === 'Keep') return 'por-feedback-btn por-feedback-btn--keep';
  if (opt === 'Modify') return 'por-feedback-btn por-feedback-btn--modify';
  if (opt === "Don't Need") return 'por-feedback-btn por-feedback-btn--dont-need';
  return 'por-feedback-btn';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ParadeOfReports({ open, onClose, fontSize }: Props) {
  const [manifest, setManifest] = useState<ParadeManifest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Selection state — which reports to include in the parade
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Parade state — stepping through selected reports
  const [parading, setParading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [feedbackMap, setFeedbackMap] = useState<Record<number, ParadeFeedback>>({});
  const [currentNotes, setCurrentNotes] = useState('');

  const iframeRef = useRef<HTMLIFrameElement>(null);

  // ── Load manifest ──
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError('');
    manageAction('start_parade', {})
      .then((res: any) => {
        const data = res?.data || res;
        setManifest(data);
        // Pre-select all reports that have sample data
        const ids = new Set<number>();
        for (const g of data.groups || []) {
          for (const r of g.reports || []) {
            if (r.has_sample_data) ids.add(r.id);
          }
        }
        setSelectedIds(ids);
      })
      .catch((e: any) => setError(e?.message || 'Failed to load reports'))
      .finally(() => setLoading(false));
  }, [open]);

  // ── Selected reports in parade order ──
  const paradeReports: ParadeReport[] = [];
  if (manifest) {
    for (const g of manifest.groups) {
      for (const r of g.reports) {
        if (selectedIds.has(r.id)) paradeReports.push(r);
      }
    }
  }

  const currentReport = parading ? paradeReports[currentIndex] : null;

  // ── Toggle selection ──
  const toggleReport = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  // ── Select/deselect group ──
  const toggleGroup = useCallback((group: ParadeGroup) => {
    const groupIds = group.reports.map(r => r.id);
    const allSelected = groupIds.every(id => selectedIds.has(id));
    setSelectedIds(prev => {
      const next = new Set(prev);
      for (const id of groupIds) {
        if (allSelected) next.delete(id); else next.add(id);
      }
      return next;
    });
  }, [selectedIds]);

  // ── Start parade ──
  const startParade = useCallback(() => {
    if (paradeReports.length === 0) return;
    setParading(true);
    setCurrentIndex(0);
    setCurrentNotes('');
  }, [paradeReports.length]);

  // ── Save feedback and advance ──
  const submitFeedback = useCallback(async (decision: string) => {
    if (!currentReport) return;

    const feedback: ParadeFeedback = { decision: decision as any, notes: currentNotes };
    setFeedbackMap(prev => ({ ...prev, [currentReport.id]: feedback }));

    // Save to server
    try {
      await manageAction('save_parade_feedback', {
        report_id: currentReport.id,
        feedback: decision,
        notes: currentNotes,
      });
    } catch (e) {
      console.warn('Failed to save parade feedback:', e);
    }

    // Advance
    if (currentIndex < paradeReports.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setCurrentNotes('');
    } else {
      // Parade complete
      setParading(false);
    }
  }, [currentReport, currentNotes, currentIndex, paradeReports.length]);

  // ── Skip ──
  const skipReport = useCallback(() => {
    if (currentIndex < paradeReports.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setCurrentNotes('');
    } else {
      setParading(false);
    }
  }, [currentIndex, paradeReports.length]);

  // ── Back ──
  const goBack = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      setCurrentNotes('');
    }
  }, [currentIndex]);

  if (!open) return null;

  // ── Summary view (after parade) ──
  const showSummary = !parading && Object.keys(feedbackMap).length > 0;

  // Set the --por-fs custom property for font size on the root element
  const rootStyle = { '--por-fs': `${fontSize || 13}px` } as React.CSSProperties;

  return (
    <div className="por-overlay" onClick={onClose}>
      <div
        className={`por-dialog${parading ? ' por-dialog--parading' : ''}`}
        style={rootStyle}
        onClick={e => e.stopPropagation()}
      >
        {/* -- Header -- */}
        <div className="por-header">
          <div>
            <span className="por-title">
              {parading
                ? `Report ${currentIndex + 1} of ${paradeReports.length}`
                : showSummary ? 'Parade Complete' : 'Parade of Reports'}
            </span>
            {parading && currentReport && (
              <span className="por-subtitle">
                {currentReport.name}
              </span>
            )}
          </div>
          <button
            className="por-btn por-btn--sm"
            onClick={parading ? () => setParading(false) : onClose}
          >
            {parading ? 'Exit Parade' : 'Close'}
          </button>
        </div>

        {/* -- Body -- */}
        <div className={`por-body${parading ? ' por-body--parading' : ''}`}>
          {loading && (
            <div className="por-loading">Loading reports...</div>
          )}

          {error && (
            <div className="por-error">{error}</div>
          )}

          {/* -- Selection view -- */}
          {!loading && !error && !parading && !showSummary && manifest && (
            <div>
              <p className="por-instructions">
                Select the reports you want to review. Each will render with
                sample data so you can see what it looks like with real content.
              </p>
              {manifest.groups.map(group => (
                <div key={group.name} className="por-group">
                  <div className="por-group-header" onClick={() => toggleGroup(group)}>
                    <input
                      type="checkbox"
                      className="por-checkbox"
                      checked={group.reports.every(r => selectedIds.has(r.id))}
                      readOnly
                    />
                    <span>{group.name}</span>
                    <span className="por-group-desc">
                      {group.description} ({group.count})
                    </span>
                  </div>
                  {group.reports.map(r => {
                    const prior = feedbackMap[r.id];
                    return (
                      <div
                        key={r.id}
                        className={`por-report-row${!r.has_sample_data ? ' por-report-row--disabled' : ''}`}
                        onClick={() => r.has_sample_data && toggleReport(r.id)}
                      >
                        <input
                          type="checkbox"
                          className="por-checkbox"
                          checked={selectedIds.has(r.id)}
                          disabled={!r.has_sample_data}
                          readOnly
                        />
                        <span>{r.name}</span>
                        {!r.has_sample_data && (
                          <span className="por-no-sample">(no sample data yet)</span>
                        )}
                        {prior && (
                          <span className={`por-badge ${badgeClass(prior.decision)}`}>
                            {prior.decision}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}

          {/* -- Parade view -- */}
          {parading && currentReport && (
            <>
              <iframe
                ref={iframeRef}
                src={currentReport.render_url || ''}
                className="por-preview"
                title={currentReport.name}
              />
              <div className="por-feedback-panel">
                <div className="por-feedback-name">
                  {currentReport.name}
                </div>
                <div className="por-feedback-meta">
                  {currentReport.model_name} &middot; {currentReport.category}
                </div>

                {['Keep', 'Modify', "Don't Need"].map(opt => (
                  <button
                    key={opt}
                    className={feedbackBtnClass(opt)}
                    onClick={() => submitFeedback(opt)}
                  >
                    {opt}
                  </button>
                ))}

                <textarea
                  className="por-notes"
                  placeholder="Notes (optional)..."
                  value={currentNotes}
                  onChange={e => setCurrentNotes(e.target.value)}
                />

                <div className="por-nav-row">
                  <button
                    className="por-btn"
                    onClick={goBack}
                    disabled={currentIndex === 0}
                  >
                    Back
                  </button>
                  <button className="por-btn" onClick={skipReport}>
                    Skip
                  </button>
                </div>

                <div className="por-progress">
                  {currentIndex + 1} / {paradeReports.length} reports
                </div>
              </div>
            </>
          )}

          {/* -- Summary view -- */}
          {showSummary && manifest && (
            <div className="por-summary">
              <p className="por-summary-title">
                Your report selections:
              </p>
              <table className="por-summary-table">
                <thead>
                  <tr>
                    <th>Report</th>
                    <th>Decision</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {paradeReports.map(r => {
                    const fb = feedbackMap[r.id];
                    if (!fb) return null;
                    return (
                      <tr key={r.id}>
                        <td>{r.name}</td>
                        <td>
                          <span className={`por-badge ${badgeClass(fb.decision)}`}>
                            {fb.decision}
                          </span>
                        </td>
                        <td className="por-summary-notes">
                          {fb.notes || '\u2014'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="por-summary-stats">
                Keep: {Object.values(feedbackMap).filter(f => f.decision === 'Keep').length} &middot;
                Modify: {Object.values(feedbackMap).filter(f => f.decision === 'Modify').length} &middot;
                Don't Need: {Object.values(feedbackMap).filter(f => f.decision === "Don't Need").length}
              </div>
            </div>
          )}
        </div>

        {/* -- Footer -- */}
        <div className="por-footer">
          <div className="por-footer-info">
            {!parading && manifest && `${selectedIds.size} of ${manifest.total_reports} reports selected`}
          </div>
          <div className="por-footer-actions">
            {!parading && !showSummary && (
              <button
                className="por-btn--primary"
                disabled={selectedIds.size === 0}
                onClick={startParade}
              >
                Start Parade ({selectedIds.size})
              </button>
            )}
            {showSummary && (
              <>
                <button className="por-btn" onClick={() => {
                  setFeedbackMap({});
                  setParading(false);
                }}>
                  Run Again
                </button>
                <button className="por-btn--primary" onClick={onClose}>
                  Done
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ParadeOfReports;
