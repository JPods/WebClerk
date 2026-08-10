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
 * LastChecked: 2026-07-21 | WhereUsed: DataBrowser, TransactionDetailBase | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { getRecords, getRecord, saveRecord, getFormLibrary, checkoutForm, submitFormToLibrary, restoreFormFromLibrary } from '@/api/wcapi';
import type { FormLibraryEntry } from '@/api/wcapi';
import { openUniversalPrint } from '@/components/print/UniversalPrint';
import { fetchPrintLayout } from '@/hooks/usePrintLayout'; // fallback for reports without config.form
import PrintLayoutDesigner from '@/components/print/PrintLayoutDesigner';
import type { PrintLayout } from '@/components/print/printLayoutTypes';
// ParadeOfReports available at /parade route — launched as a Report record, not a dialog button

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
  /** Current list records (for list-context reports) */
  listRecords?: any[];
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
  /** Company info for print headers/footers */
  companyInfo?: any;
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
  merge:  { label: 'Template', icon: '📝' },
  screen: { label: 'Screen', icon: '🖥️' },
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
  open, model, context, selectedId, listRecords,
  theme: t, fontSize, onClose,
  onExecuteReport,
  companyInfo,
  canEditReports = true,
  canCreateReports = true,
}) => {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedModel, setLoadedModel] = useState('');
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const listRef = useRef<HTMLDivElement>(null);

  // --- DesignMode ---
  const [designMode, setDesignMode] = useState(false);
  const [designReport, setDesignReport] = useState<ReportRecord | null>(null);
  const [designLayout, setDesignLayout] = useState<PrintLayout | null>(null);
  const [designSampleData, setDesignSampleData] = useState<any>(null);


  // --- Library ---
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [libraryForms, setLibraryForms] = useState<FormLibraryEntry[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryStatus, setLibraryStatus] = useState('');

  const openLibrary = useCallback(() => {
    setLibraryOpen(true);
    setLibraryLoading(true);
    setLibraryStatus('');
    getFormLibrary(model).then(result => {
      setLibraryForms(result.forms);
      setLibraryStatus(result.forms.length === 0 ? `No forms in library for ${model}` : '');
    }).catch(err => {
      setLibraryStatus(`Library unavailable: ${err?.message || 'connection error'}`);
      setLibraryForms([]);
    }).finally(() => setLibraryLoading(false));
  }, [model]);

  const handleCheckout = useCallback(async (entry: FormLibraryEntry) => {
    setLibraryStatus('Checking out...');
    try {
      // Fetch the full report record from the library
      const fullRecord = await getRecord('report', entry.id);
      const record = (fullRecord as any)?.record || fullRecord;
      const result = await checkoutForm(entry.uuid, record);
      setLibraryStatus(`${result.action === 'created' ? 'Checked out' : 'Updated'}: ${entry.name}`);
      // Refresh the report list
      setLoadedModel('');
      setTimeout(() => setLibraryOpen(false), 1200);
    } catch (err: any) {
      setLibraryStatus(`Checkout failed: ${err?.message || 'error'}`);
    }
  }, []);

  const handleSubmitToLibrary = useCallback(async (report: ReportRecord) => {
    try {
      const result = await submitFormToLibrary(report.id);
      setLibraryStatus(`Submitted: ${result.name}`);
    } catch (err: any) {
      setLibraryStatus(`Submit failed: ${err?.message || 'error'}`);
    }
  }, []);

  const handleRestore = useCallback(async (report: ReportRecord) => {
    try {
      await restoreFormFromLibrary(report.id);
      setLoadedModel(''); // refresh
      setLibraryStatus(`Restored: ${report.name} to library original`);
    } catch (err: any) {
      setLibraryStatus(`Restore failed: ${err?.message || 'error'}`);
    }
  }, []);

  const enterDesignMode = useCallback(async (report: ReportRecord) => {
    // Load layout from report.config.form or fallback to Setting
    let layout: PrintLayout;
    const form = report.config?.form as PrintLayout | undefined;
    if (form?.sections) {
      layout = form;
    } else {
      layout = await fetchPrintLayout(model);
    }
    // Load sample data
    let sample: any = null;
    if (selectedId) {
      try {
        const res = await getRecord(model, selectedId);
        sample = (res as any)?.record || res;
      } catch { /* proceed without sample */ }
    } else if (listRecords?.length) {
      sample = context === 'list' ? { rows: listRecords.slice(0, 10) } : listRecords[0];
    }
    setDesignReport(report);
    setDesignLayout(layout);
    setDesignSampleData(sample);
    setDesignMode(true);
  }, [model, selectedId, listRecords, context]);

  const handleDesignSave = useCallback(async (layout: PrintLayout) => {
    if (!designReport) return;
    await saveRecord('report', {
      id: designReport.id,
      config: { ...(designReport.config || {}), form: layout },
    });
    // Refresh report list
    setLoadedModel('');
    setDesignMode(false);
    setDesignReport(null);
    setDesignLayout(null);
  }, [designReport]);

  const exitDesignMode = useCallback(() => {
    setDesignMode(false);
    setDesignReport(null);
    setDesignLayout(null);
    setDesignSampleData(null);
  }, []);

  // ---- Fetch reports for this model ----
  useEffect(() => {
    if (!open || !model || loadedModel === model) return;
    setLoading(true);
    getRecords('report', { model_name_filter: model }).then((result: any) => {
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
  // All reports show in both contexts — reports apply to the model, not to a specific view.
  // The context only affects execution (list = all selected, detail = one record).
  const filteredReports = reports;

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
  const executeReport = useCallback(async (report: ReportRecord) => {
    if (onExecuteReport) {
      onExecuteReport(report);
      onClose();
      return;
    }
    const ot = (report.output_type || '').toLowerCase();

    // Print reports → universal print renderer (JSON-driven)
    if (ot === 'print') {
      onClose();
      try {
        const form = report.config?.form;
        const layout = form || await fetchPrintLayout(model);
        const hasDataTable = layout?.sections?.some((s: any) => s.type === 'data_table');

        const printOpts = { reportConfig: report.config || {} };

        if (hasDataTable && listRecords?.length) {
          // List report — pass current list records as rows
          await openUniversalPrint({ rows: listRecords }, companyInfo, layout, printOpts);
        } else if (context === 'detail' && selectedId) {
          // Single-record form
          const recordRes = await getRecord(model, selectedId);
          const record = (recordRes as any)?.record || recordRes;
          await openUniversalPrint(record, companyInfo, layout, printOpts);
        } else if (listRecords?.length) {
          // List context, no data_table section — still pass rows
          await openUniversalPrint({ rows: listRecords }, companyInfo, layout, printOpts);
        }
      } catch (e) {
        console.error('[ReportsDialog] Print failed:', e);
      }
      return;
    }

    // Screen reports → navigate to config.screen_url (e.g. /parade)
    if (ot === 'screen') {
      const screenUrl = (report.config as any)?.screen_url;
      if (screenUrl) {
        window.open(screenUrl, '_blank');
      }
      onClose();
      return;
    }

    // Export reports → trigger CSV download via wcapi
    if (ot === 'export') {
      window.open(`/wcapi/export/?model=${encodeURIComponent(model)}&format=csv`, '_blank');
      onClose();
      return;
    }

    // Fallback — open report endpoint in new tab
    const reportName = encodeURIComponent(report.name);
    const modelName = encodeURIComponent(model);
    let url = `/wcapi/report/?report=${reportName}&model=${modelName}`;
    if (context === 'detail' && selectedId) {
      url += `&id=${selectedId}`;
    }
    window.open(url, '_blank');
    onClose();
  }, [onExecuteReport, model, context, selectedId, onClose]);


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

      {/* Full-screen editor overlay — separate from ReportsDialog */}
      {designMode && (
        <div data-wc="reports-editor-overlay"
          style={{
            position: 'fixed', inset: 0, zIndex: 9500,
            background: 'rgba(0,0,0,0.8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <div style={{
            width: '96vw', height: '94vh', maxWidth: 1900,
            background: t.surface, border: `1px solid ${t.border}`,
            borderRadius: 8, display: 'flex', flexDirection: 'column',
            boxShadow: '0 12px 48px rgba(0,0,0,0.7)',
            overflow: 'hidden',
          }}>
            {designMode && designReport && designLayout && (
              <PrintLayoutDesigner
                report={designReport}
                model={model}
                layout={designLayout}
                theme={t}
                fontSize={fontSize}
                companyInfo={companyInfo}
                sampleData={designSampleData}
                onSave={handleDesignSave}
                onClose={exitDesignMode}
              />
            )}
          </div>
        </div>
      )}

      {/* Reports list dialog */}
      <div data-wc="reports-dialog"
        style={{
          background: t.surface, border: `1px solid ${t.border}`,
          borderRadius: 8,
          width: 620,
          maxHeight: '85vh',
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
          display: 'grid', gridTemplateColumns: '70px 1fr 72px',
          gap: 8, padding: '6px 16px',
          borderBottom: `1px solid ${t.borderLight}`,
          fontSize: fontSize - 2, fontWeight: 700, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: '0.05em',
        }}>
          <span>Type</span>
          <span>Report Name</span>
          <span style={{ textAlign: 'center' }}>Output</span>
        </div>

        {/* Body — report list */}
        <div style={{ flex: 1, display: 'flex', minHeight: 120, overflow: 'hidden' }}>

        <div ref={listRef} style={{
          flex: 1, overflowY: 'auto', padding: '4px 0',
        }}>
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
            const hasForm = !!(report.config as any)?.form;
            const editorTag = hasForm ? 'layout' : null;
            const ot = OUTPUT_TYPE_LABELS[report.output_type || 'print'] || OUTPUT_TYPE_LABELS.print;

            return (
              <div key={report.id}
                data-wc="reports-dialog-row"
                onClick={(e) => {
                  if (e.shiftKey && canEditReports) { enterDesignMode(report); return; }
                  setSelectedIndex(i);
                }}
                onDoubleClick={() => executeReport(report)}
                style={{
                  display: 'grid', gridTemplateColumns: '70px 1fr 72px',
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
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 1,
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <span>{ot.icon}</span>
                    <span>{ot.label}</span>
                  </span>
                  {editorTag && (
                    <span style={{
                      fontSize: fontSize - 4, padding: '0px 4px', borderRadius: 3,
                      background: '#059669',
                      color: '#fff', fontWeight: 600, letterSpacing: '0.02em',
                    }}>{editorTag}</span>
                  )}
                </span>

              </div>
            );
          })}
        </div>

        {/* Library pane — shows available forms from Andi/Alice */}
        {libraryOpen && (
          <div style={{
            flex: 1, borderLeft: `1px solid ${t.border}`,
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
          }}>
            <div style={{
              padding: '8px 12px', borderBottom: `1px solid ${t.borderLight}`,
              fontSize: fontSize - 1, color: t.accent, fontWeight: 700,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span>Form Library — {model}</span>
              <span style={{ fontSize: fontSize - 2, color: t.textMuted, fontWeight: 400 }}>
                Double-click to check out
              </span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
              {libraryLoading && (
                <div style={{ padding: 16, color: t.textMuted, textAlign: 'center' }}>
                  Loading library...
                </div>
              )}
              {!libraryLoading && libraryForms.length === 0 && (
                <div style={{ padding: '24px 16px', color: t.textDim, textAlign: 'center' }}>
                  {libraryStatus || `No forms available for ${model}`}
                </div>
              )}
              {!libraryLoading && libraryForms.map((entry) => (
                <div key={entry.uuid}
                  onDoubleClick={() => handleCheckout(entry)}
                  style={{
                    padding: '8px 16px', cursor: 'pointer',
                    borderBottom: `1px solid ${t.borderLight}`,
                    display: 'grid', gridTemplateColumns: '1fr 80px 80px',
                    gap: 8, alignItems: 'center',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize, color: t.text }}>
                      {entry.name}
                    </div>
                    {entry.description && (
                      <div style={{ fontSize: fontSize - 2, color: t.textMuted, marginTop: 1 }}>
                        {entry.description}
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: fontSize - 2, color: t.textDim, textAlign: 'center' }}>
                    {entry.row_count} rows
                  </span>
                  <span style={{ fontSize: fontSize - 2, color: t.textDim, textAlign: 'center' }}>
                    {entry.field_count} fields
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}


        </div>{/* end body flex row */}

        {/* Footer — Library select, Edit button, New Report select */}
        <div style={{
          padding: '10px 16px', borderTop: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            {context === 'detail' && selectedId ? `Record #${selectedId}` : 'List reports'}
            {' · Double-click to print · '}
            <span style={{ color: t.textDim }}>
              {navigator.platform.includes('Mac') ? '⌘P' : 'Ctrl+P'} = Primary
            </span>
            {libraryStatus && (
              <span style={{ marginLeft: 8, color: t.accent }}>{libraryStatus}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Library select */}
            <select
              data-wc="reports-library-select"
              value=""
              onChange={(e) => {
                const action = e.target.value;
                e.target.value = '';
                if (action === 'browse') openLibrary();
                else if (action === 'submit' && selectedIndex >= 0 && selectedIndex < filteredReports.length) {
                  handleSubmitToLibrary(filteredReports[selectedIndex]);
                }
                else if (action === 'restore' && selectedIndex >= 0 && selectedIndex < filteredReports.length) {
                  handleRestore(filteredReports[selectedIndex]);
                }
              }}
              style={{
                padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
                fontSize: fontSize - 1, fontWeight: 600,
                background: t.surface, border: `1px solid ${t.border}`,
                color: t.text, appearance: 'auto',
              }}
            >
              <option value="" disabled>Library</option>
              <option value="browse">Browse</option>
              {selectedIndex >= 0 && selectedIndex < filteredReports.length && (
                <option value="submit">Submit</option>
              )}
              {selectedIndex >= 0 && selectedIndex < filteredReports.length &&
                (filteredReports[selectedIndex]?.config as any)?.library_original && (
                <option value="restore">Restore</option>
              )}
            </select>

            {/* Edit — smart button, routes to correct editor */}
            {canEditReports && selectedIndex >= 0 && selectedIndex < filteredReports.length && (
              <button
                data-wc="reports-edit-button"
                onClick={() => enterDesignMode(filteredReports[selectedIndex])}
                title="Edit report layout"
                style={{
                  padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
                  fontSize: fontSize - 1, fontWeight: 600,
                  background: 'none', border: `1px solid ${t.accent}`,
                  color: t.accent,
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
              >
                Edit
              </button>
            )}

            {/* New Report select */}
            {canCreateReports && (
              <select
                data-wc="reports-new-select"
                value=""
                onChange={(e) => {
                  const outputType = e.target.value;
                  e.target.value = '';
                  if (!outputType) return;
                  saveRecord('report', {
                    name: `New ${outputType.charAt(0).toUpperCase() + outputType.slice(1)} Report`,
                    model_name: model,
                    output_type: outputType,
                    category: 'report',
                    sort_order: 99,
                    config: {},
                  }).then((res: any) => {
                    const newId = res?.record?.id || res?.id;
                    setLoadedModel(''); // refresh list
                    if (newId) {
                      window.open(`/report?search=${newId}`, '_blank');
                    }
                  });
                }}
                style={{
                  padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
                  fontSize: fontSize - 1, fontWeight: 600,
                  background: t.accent, border: 'none',
                  color: '#fff', appearance: 'auto',
                }}
              >
                <option value="" disabled style={{ color: '#000' }}>New Report</option>
                <option value="print" style={{ color: '#000' }}>Print</option>
                <option value="email" style={{ color: '#000' }}>Email</option>
                <option value="export" style={{ color: '#000' }}>Export</option>
                <option value="label" style={{ color: '#000' }}>Label</option>
                <option value="screen" style={{ color: '#000' }}>Screen</option>
                <option value="api" style={{ color: '#000' }}>API</option>
              </select>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsDialog;
export type { Props as ReportsDialogProps };
