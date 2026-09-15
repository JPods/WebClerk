/**
 * ReportViewer — generates and displays a PDF from a pdfme template + record data.
 *
 * Used when a user clicks "Print" on an invoice, order, etc.
 * Loads the report template from the report record's data.template field,
 * fetches the record, maps fields, generates PDF, and displays it.
 *
 * Usage:
 *   <ReportViewer
 *     reportName="Invoice - Standard"
 *     modelName="invoice"
 *     recordId={42}
 *     onClose={() => setShowViewer(false)}
 *   />
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { generate } from '@pdfme/generator';
import { text, image } from '@pdfme/schemas';
import type { Template } from '@pdfme/common';
import { getRecord, getRecords } from '@/api/wcapi';
import { getDefaultTemplate } from '@/config/defaultReportTemplates';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ReportViewerProps {
  /** Report name (e.g. 'Invoice - Standard') — matches reportLists.ts */
  reportName: string;
  /** wcapi model name (e.g. 'invoice') */
  modelName: string;
  /** Record ID to print */
  recordId: number;
  /** Close handler */
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Map a flat record object to pdfme input values.
 * Template field names are matched against record keys.
 * Missing keys get empty strings.
 */
function mapRecordToInputs(
  template: Template,
  record: Record<string, any>,
): Record<string, string> {
  const inputs: Record<string, string> = {};
  for (const page of template.schemas) {
    for (const field of page) {
      if (typeof field === 'object' && 'name' in field) {
        const name = (field as any).name;
        const val = record[name];
        inputs[name] = val != null ? String(val) : '';
      }
    }
  }
  return inputs;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ReportViewer({
  reportName,
  modelName,
  recordId,
  onClose,
}: ReportViewerProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const generatePdf = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Try to load template from wc3 report record
      let template: Template | undefined;
      try {
        const reportRes = (await getRecords('report', {
          name: reportName,
          limit: 1,
        })) as any;
        const reportRecord = reportRes?.results?.[0];
        if (reportRecord?.config?.template) {
          template = reportRecord.config.template as Template;
        }
      } catch {
        // Fall through to default template
      }

      // 2. Fall back to default template
      if (!template) {
        template = getDefaultTemplate(reportName);
      }

      if (!template) {
        setError(
          `No template found for report "${reportName}". Open Report Designer to create one.`,
        );
        setLoading(false);
        return;
      }

      // 3. Load the record data
      const recordRes = (await getRecord(modelName, recordId)) as any;
      const record = recordRes?.record || recordRes || {};

      // 4. Map record fields to template inputs
      const inputs = mapRecordToInputs(template, record);

      // 5. Generate PDF
      const pdf = await generate({
        template,
        inputs: [inputs],
        plugins: { text, image },
      });

      // 6. Create blob URL for display
      const blob = new Blob([pdf.buffer], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (err: any) {
      console.error('[ReportViewer] PDF generation failed:', err);
      setError(err?.message || 'Failed to generate PDF');
    } finally {
      setLoading(false);
    }
  }, [reportName, modelName, recordId]);

  useEffect(() => {
    generatePdf();
    return () => {
      // Cleanup blob URL
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generatePdf]);

  const handleDownload = useCallback(() => {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = pdfUrl;
    a.download = `${reportName.replace(/\s+/g, '_')}_${recordId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, reportName, recordId]);

  return (
    <div
      data-wc="report-viewer"
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl flex flex-col"
        style={{ width: '90vw', height: '90vh', maxWidth: 1000 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            {reportName} &mdash; {modelName} #{recordId}
          </h2>
          <div className="flex items-center gap-2">
            {pdfUrl && (
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition"
              >
                Download PDF
              </button>
            )}
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
            >
              Close
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden">
          {loading && (
            <div className="flex items-center justify-center h-full text-sm text-gray-500">
              Generating PDF...
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full px-8">
              <div className="text-center">
                <div className="text-red-500 text-sm font-medium mb-2">
                  Error
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {error}
                </div>
              </div>
            </div>
          )}
          {pdfUrl && !loading && (
            <iframe
              ref={iframeRef}
              src={pdfUrl}
              className="w-full h-full border-0"
              title="Report PDF"
            />
          )}
        </div>
      </div>
    </div>
  );
}
