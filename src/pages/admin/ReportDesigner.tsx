/**
 * ReportDesigner — pdfme-based visual report template editor.
 *
 * Replaces wc2's ReportDesign form. Users visually design report templates
 * that generate PDFs. Templates are saved to the wc3 Report model via wcapi.
 *
 * Flow:
 *   1. Load report records from wcapi
 *   2. Select a report to edit (or create new)
 *   3. pdfme Designer for visual template editing
 *   4. Save template JSON to report.config.template
 *   5. Preview — generate PDF from template + sample data
 *   6. Download the generated PDF
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Designer } from '@pdfme/ui';
import { generate } from '@pdfme/generator';
import type { Template } from '@pdfme/common';
import { getRecords, saveRecord } from '@/api/wcapi';
import { getDefaultTemplate } from '@/config/defaultReportTemplates';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReportRecord {
  id: number;
  name: string;
  description: string;
  model_name: string;
  output_type: string;
  category: string;
  sort_order: number;
  data: { template?: Template; [k: string]: unknown };
}

// ---------------------------------------------------------------------------
// Blank template for new reports
// ---------------------------------------------------------------------------

const EMPTY_TEMPLATE = {
  basePdf: { width: 215.9, height: 279.4, padding: [12.7, 12.7, 12.7, 12.7] },
  schemas: [
    [
      {
        name: 'title',
        type: 'text',
        position: { x: 20, y: 20 },
        width: 100,
        height: 10,
        fontSize: 16,
        fontWeight: 'bold',
      },
    ],
  ],
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ReportDesigner() {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState('');

  const designerRef = useRef<Designer | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedReport = reports.find((r) => r.id === selectedId) || null;

  // -- Load reports --
  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      const res = (await getRecords('report', {
        limit: 200,
        ordering: 'model_name,sort_order',
      })) as any;
      setReports((res?.results || []) as ReportRecord[]);
    } catch (err) {
      console.error('[ReportDesigner] Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // -- Initialize / update Designer when selection changes --
  useEffect(() => {
    if (!containerRef.current || !selectedReport) return;

    // Destroy previous designer
    if (designerRef.current) {
      designerRef.current.destroy();
      designerRef.current = null;
    }

    // Resolve template: saved > default > empty
    // Check both config.pdfme_template and config.template for backward compat
    let template: Template =
      selectedReport.config?.pdfme_template ||
      selectedReport.config?.template ||
      getDefaultTemplate(selectedReport.name) ||
      EMPTY_TEMPLATE;

    // Ensure template has basePdf — use letter-size object format (works in Vite dev)
    if (!template.basePdf) {
      template = { ...template, basePdf: { width: 215.9, height: 279.4, padding: [12.7, 12.7, 12.7, 12.7] } };
    }

    try {
      const designer = new Designer({
        domContainer: containerRef.current,
        template: template as any,
      });
      designerRef.current = designer;
    } catch (err) {
      console.error('[ReportDesigner] Failed to initialize Designer:', err);
      setStatusMsg('Failed to initialize template editor');
    }

    return () => {
      if (designerRef.current) {
        designerRef.current.destroy();
        designerRef.current = null;
      }
    };
  }, [selectedReport]);

  // -- Save template --
  const handleSave = useCallback(async () => {
    if (!designerRef.current || !selectedReport) return;

    try {
      setSaving(true);
      const template = designerRef.current.getTemplate();

      // Merge template into existing config
      const newConfig = { ...(selectedReport.config || {}), pdfme_template: template };

      await saveRecord('report', {
        id: selectedReport.id,
        config: newConfig,
      });

      setStatusMsg('Template saved');
      setTimeout(() => setStatusMsg(''), 3000);

      // Refresh report list to pick up saved data
      await loadReports();
    } catch (err: any) {
      console.error('[ReportDesigner] Save failed:', err);
      setStatusMsg(`Save failed: ${err?.message || 'unknown error'}`);
    } finally {
      setSaving(false);
    }
  }, [selectedReport, loadReports]);

  // -- Preview (generate PDF) --
  const handlePreview = useCallback(async () => {
    if (!designerRef.current) return;

    try {
      const template = designerRef.current.getTemplate();

      // Build sample data — fill every field with its name as placeholder
      const sampleInputs: Record<string, string> = {};
      for (const page of template.schemas) {
        for (const field of page) {
          if (typeof field === 'object' && 'name' in field) {
            sampleInputs[(field as any).name] = `[${(field as any).name}]`;
          }
        }
      }

      const pdf = await generate({
        template,
        inputs: [sampleInputs],
      });

      // Cleanup previous preview URL
      if (previewUrl) URL.revokeObjectURL(previewUrl);

      const blob = new Blob([pdf.buffer], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch (err: any) {
      console.error('[ReportDesigner] Preview failed:', err);
      setStatusMsg(`Preview failed: ${err?.message || 'unknown error'}`);
    }
  }, [previewUrl]);

  // -- Download preview --
  const handleDownload = useCallback(() => {
    if (!previewUrl || !selectedReport) return;
    const a = document.createElement('a');
    a.href = previewUrl;
    a.download = `${selectedReport.name.replace(/\s+/g, '_')}_preview.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [previewUrl, selectedReport]);

  // -- Cleanup --
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div data-wc="report-designer" className="flex h-full bg-gray-50 dark:bg-gray-900">
      {/* ── Sidebar: Report list ── */}
      <div className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-sm font-bold text-gray-900 dark:text-white">
            Report Designer
          </h1>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-1">
            Select a report to edit its PDF template
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-xs text-gray-500">Loading reports...</div>
          ) : reports.length === 0 ? (
            <div className="p-4 text-xs text-gray-500">
              No reports found. Create reports in the DataBrowser first.
            </div>
          ) : (
            <ul className="py-1">
              {reports.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => {
                      setSelectedId(r.id);
                      setPreviewUrl(null);
                      setStatusMsg('');
                    }}
                    className={`w-full text-left px-4 py-2 text-xs transition ${
                      selectedId === r.id
                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="font-medium truncate">{r.name}</div>
                    <div className="text-[10px] text-gray-400 mt-0.5 truncate">
                      {r.model_name} &middot; {r.output_type} &middot; {r.category}
                    </div>
                    {(r.config?.pdfme_template || r.config?.template) && (
                      <span className="inline-block mt-0.5 px-1.5 py-0.5 text-[9px] rounded bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400">
                        has template
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="text-xs text-gray-600 dark:text-gray-400">
            {selectedReport ? (
              <>
                Editing: <strong>{selectedReport.name}</strong> ({selectedReport.model_name})
              </>
            ) : (
              'Select a report from the sidebar'
            )}
          </div>
          <div className="flex items-center gap-2">
            {statusMsg && (
              <span className="text-xs text-green-600 dark:text-green-400 mr-2">
                {statusMsg}
              </span>
            )}
            <button
              onClick={handlePreview}
              disabled={!selectedReport}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 transition"
            >
              Preview PDF
            </button>
            {previewUrl && (
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700 transition"
              >
                Download
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!selectedReport || saving}
              className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition"
            >
              {saving ? 'Saving...' : 'Save Template'}
            </button>
          </div>
        </div>

        {/* Designer container */}
        {selectedReport ? (
          <div className="flex-1 relative">
            <div
              ref={containerRef}
              className="absolute inset-0"
              style={{ minHeight: 500 }}
            />
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
            Select a report to begin editing its PDF template
          </div>
        )}

        {/* Preview pane (slides up from bottom when active) */}
        {previewUrl && (
          <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800" style={{ height: '40%' }}>
            <div className="flex items-center justify-between px-4 py-1 border-b border-gray-100 dark:border-gray-700">
              <span className="text-[10px] font-semibold text-gray-500 uppercase">
                Preview
              </span>
              <button
                onClick={() => {
                  if (previewUrl) URL.revokeObjectURL(previewUrl);
                  setPreviewUrl(null);
                }}
                className="text-[10px] text-gray-400 hover:text-gray-600"
              >
                Close Preview
              </button>
            </div>
            <iframe
              src={previewUrl}
              className="w-full border-0"
              style={{ height: 'calc(100% - 28px)' }}
              title="PDF Preview"
            />
          </div>
        )}
      </div>
    </div>
  );
}
