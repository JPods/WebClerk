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
 * LastChecked: 2026-08-07 | WhereUsed: ReportsDialog, Router | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { manageAction, saveRecord } from '@/api/wcapi';

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
  theme: {
    bg: string; surface: string; surfaceAlt: string;
    border: string; borderLight: string;
    text: string; textMuted: string; textDim: string;
    accent: string; accentGreen: string; accentGold: string; accentRed: string;
    [k: string]: string;
  };
  fontSize: number;
}

// ---------------------------------------------------------------------------
// Feedback button colors
// ---------------------------------------------------------------------------

const FEEDBACK_COLORS: Record<string, { bg: string; border: string }> = {
  'Keep':        { bg: '#1a3a1a', border: '#2d5a2d' },
  'Modify':      { bg: '#3a3a1a', border: '#5a5a2d' },
  "Don't Need":  { bg: '#3a1a1a', border: '#5a2d2d' },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ParadeOfReports({ open, onClose, theme, fontSize }: Props) {
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

  const fs = fontSize || 13;
  const S: Record<string, React.CSSProperties> = {
    overlay: {
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.7)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    },
    dialog: {
      background: theme.bg, border: `1px solid ${theme.border}`,
      borderRadius: 8, width: parading ? '95vw' : 720,
      maxHeight: '90vh', display: 'flex', flexDirection: 'column',
      color: theme.text, fontSize: fs,
    },
    header: {
      padding: '16px 20px', borderBottom: `1px solid ${theme.border}`,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    },
    body: {
      flex: 1, overflow: 'auto', padding: parading ? 0 : 20,
      display: parading ? 'flex' : 'block',
    },
    footer: {
      padding: '12px 20px', borderTop: `1px solid ${theme.border}`,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    },
    group: {
      marginBottom: 16,
    },
    groupHeader: {
      display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
      padding: '6px 0', fontWeight: 600, color: theme.accent,
    },
    reportRow: {
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '4px 0 4px 24px', cursor: 'pointer',
    },
    checkbox: {
      width: 16, height: 16, cursor: 'pointer',
    },
    // Parade view
    preview: {
      flex: 1, border: 'none', background: '#fff',
    },
    feedbackPanel: {
      width: 280, padding: 16, borderLeft: `1px solid ${theme.border}`,
      display: 'flex', flexDirection: 'column', gap: 12,
    },
    feedbackBtn: {
      padding: '10px 16px', border: '1px solid', borderRadius: 6,
      cursor: 'pointer', fontSize: fs, fontWeight: 500,
      color: theme.text, textAlign: 'center' as const,
    },
    notesArea: {
      width: '100%', minHeight: 80, padding: 8,
      background: theme.surfaceAlt, border: `1px solid ${theme.borderLight}`,
      borderRadius: 4, color: theme.text, fontSize: fs - 1,
      resize: 'vertical' as const,
    },
    btn: {
      padding: '8px 20px', borderRadius: 6, cursor: 'pointer',
      border: `1px solid ${theme.border}`, background: theme.surface,
      color: theme.text, fontSize: fs,
    },
    btnPrimary: {
      padding: '8px 20px', borderRadius: 6, cursor: 'pointer',
      border: 'none', background: theme.accent,
      color: '#fff', fontSize: fs, fontWeight: 600,
    },
  };

  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.dialog} onClick={e => e.stopPropagation()}>
        {/* ── Header ── */}
        <div style={S.header}>
          <div>
            <span style={{ fontWeight: 700, fontSize: fs + 2 }}>
              {parading
                ? `Report ${currentIndex + 1} of ${paradeReports.length}`
                : showSummary ? 'Parade Complete' : 'Parade of Reports'}
            </span>
            {parading && currentReport && (
              <span style={{ color: theme.textMuted, marginLeft: 12 }}>
                {currentReport.name}
              </span>
            )}
          </div>
          <button
            style={{ ...S.btn, padding: '4px 12px' }}
            onClick={parading ? () => setParading(false) : onClose}
          >
            {parading ? 'Exit Parade' : 'Close'}
          </button>
        </div>

        {/* ── Body ── */}
        <div style={S.body}>
          {loading && (
            <div style={{ padding: 40, textAlign: 'center', color: theme.textMuted }}>
              Loading reports...
            </div>
          )}

          {error && (
            <div style={{ padding: 20, color: theme.accentRed }}>{error}</div>
          )}

          {/* ── Selection view ── */}
          {!loading && !error && !parading && !showSummary && manifest && (
            <div>
              <p style={{ color: theme.textMuted, marginBottom: 16 }}>
                Select the reports you want to review. Each will render with
                sample data so you can see what it looks like with real content.
              </p>
              {manifest.groups.map(group => (
                <div key={group.name} style={S.group}>
                  <div style={S.groupHeader} onClick={() => toggleGroup(group)}>
                    <input
                      type="checkbox"
                      style={S.checkbox}
                      checked={group.reports.every(r => selectedIds.has(r.id))}
                      readOnly
                    />
                    <span>{group.name}</span>
                    <span style={{ color: theme.textDim, fontWeight: 400, fontSize: fs - 1 }}>
                      {group.description} ({group.count})
                    </span>
                  </div>
                  {group.reports.map(r => {
                    const prior = feedbackMap[r.id];
                    return (
                      <div
                        key={r.id}
                        style={{
                          ...S.reportRow,
                          opacity: r.has_sample_data ? 1 : 0.5,
                        }}
                        onClick={() => r.has_sample_data && toggleReport(r.id)}
                      >
                        <input
                          type="checkbox"
                          style={S.checkbox}
                          checked={selectedIds.has(r.id)}
                          disabled={!r.has_sample_data}
                          readOnly
                        />
                        <span>{r.name}</span>
                        {!r.has_sample_data && (
                          <span style={{ color: theme.textDim, fontSize: fs - 2 }}>
                            (no sample data yet)
                          </span>
                        )}
                        {prior && (
                          <span style={{
                            fontSize: fs - 2, padding: '1px 6px', borderRadius: 3,
                            background: FEEDBACK_COLORS[prior.decision || '']?.bg || theme.surfaceAlt,
                            border: `1px solid ${FEEDBACK_COLORS[prior.decision || '']?.border || theme.borderLight}`,
                          }}>
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

          {/* ── Parade view ── */}
          {parading && currentReport && (
            <>
              <iframe
                ref={iframeRef}
                src={currentReport.render_url || ''}
                style={S.preview}
                title={currentReport.name}
              />
              <div style={S.feedbackPanel}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {currentReport.name}
                </div>
                <div style={{ color: theme.textMuted, fontSize: fs - 1, marginBottom: 8 }}>
                  {currentReport.model_name} &middot; {currentReport.category}
                </div>

                {['Keep', 'Modify', "Don't Need"].map(opt => (
                  <button
                    key={opt}
                    style={{
                      ...S.feedbackBtn,
                      ...(FEEDBACK_COLORS[opt] || {}),
                    }}
                    onClick={() => submitFeedback(opt)}
                  >
                    {opt}
                  </button>
                ))}

                <textarea
                  style={S.notesArea}
                  placeholder="Notes (optional)..."
                  value={currentNotes}
                  onChange={e => setCurrentNotes(e.target.value)}
                />

                <div style={{ display: 'flex', gap: 8, marginTop: 'auto' }}>
                  <button
                    style={S.btn}
                    onClick={goBack}
                    disabled={currentIndex === 0}
                  >
                    Back
                  </button>
                  <button style={S.btn} onClick={skipReport}>
                    Skip
                  </button>
                </div>

                <div style={{ fontSize: fs - 2, color: theme.textDim, marginTop: 8 }}>
                  {currentIndex + 1} / {paradeReports.length} reports
                </div>
              </div>
            </>
          )}

          {/* ── Summary view ── */}
          {showSummary && manifest && (
            <div style={{ padding: 20 }}>
              <p style={{ marginBottom: 16, fontWeight: 600 }}>
                Your report selections:
              </p>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${theme.border}` }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Report</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Decision</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {paradeReports.map(r => {
                    const fb = feedbackMap[r.id];
                    if (!fb) return null;
                    return (
                      <tr key={r.id} style={{ borderBottom: `1px solid ${theme.borderLight}` }}>
                        <td style={{ padding: '6px 8px' }}>{r.name}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: 3,
                            background: FEEDBACK_COLORS[fb.decision || '']?.bg || theme.surfaceAlt,
                            border: `1px solid ${FEEDBACK_COLORS[fb.decision || '']?.border || theme.borderLight}`,
                          }}>
                            {fb.decision}
                          </span>
                        </td>
                        <td style={{ padding: '6px 8px', color: theme.textMuted }}>
                          {fb.notes || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div style={{ marginTop: 16, color: theme.textMuted, fontSize: fs - 1 }}>
                Keep: {Object.values(feedbackMap).filter(f => f.decision === 'Keep').length} &middot;
                Modify: {Object.values(feedbackMap).filter(f => f.decision === 'Modify').length} &middot;
                Don't Need: {Object.values(feedbackMap).filter(f => f.decision === "Don't Need").length}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div style={S.footer}>
          <div style={{ color: theme.textMuted, fontSize: fs - 1 }}>
            {!parading && manifest && `${selectedIds.size} of ${manifest.total_reports} reports selected`}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {!parading && !showSummary && (
              <button
                style={{
                  ...S.btnPrimary,
                  opacity: selectedIds.size === 0 ? 0.5 : 1,
                }}
                disabled={selectedIds.size === 0}
                onClick={startParade}
              >
                Start Parade ({selectedIds.size})
              </button>
            )}
            {showSummary && (
              <>
                <button style={S.btn} onClick={() => {
                  setFeedbackMap({});
                  setParading(false);
                }}>
                  Run Again
                </button>
                <button style={S.btnPrimary} onClick={onClose}>
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
