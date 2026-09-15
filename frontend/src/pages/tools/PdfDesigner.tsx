/* LastChecked: 2026-08-10 | WhereUsed: /pdf-designer, ReportsDialog | WhoCreated: Claude */
import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "../../store/hooks";
import apiClient from "../../api/axios";

interface PdfDesignerProps {
  /** Report record — if provided, loads its pdfme_template from config */
  report?: { id: number; name: string; config?: Record<string, unknown> };
  /** Model name — if provided, fetches fields from /wcapi/_report_fields/ */
  model?: string;
}

const DEFAULT_TEMPLATE = {
  basePdf: { width: 210, height: 297, padding: [20, 20, 20, 20] },
  schemas: [
    [
      {
        name: "title",
        type: "text",
        position: { x: 20, y: 20 },
        width: 170,
        height: 10,
        fontSize: 18,
      },
      {
        name: "body",
        type: "text",
        position: { x: 20, y: 40 },
        width: 170,
        height: 200,
        fontSize: 12,
      },
    ],
  ],
  columns: ["title", "body"],
  sampledata: [{ title: "Document Title", body: "Body content goes here." }],
};

const PdfDesigner: React.FC<PdfDesignerProps> = ({ report, model } = {}) => {
  const designerRef = useRef<HTMLDivElement>(null);
  const designerInstance = useRef<any>(null);
  const { user } = useAppSelector((state) => state.auth);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch model fields and build template
  useEffect(() => {
    if (!designerRef.current || designerInstance.current) return;

    const init = async () => {
      // Start with report's existing pdfme_template or default
      let template: any = DEFAULT_TEMPLATE;
      if (report?.config?.pdfme_template) {
        template = report.config.pdfme_template;
      }

      // Fetch model fields to populate columns (available field names)
      if (model) {
        try {
          const res = await fetch(`/wcapi/_report_fields/?model=${encodeURIComponent(model)}`, { credentials: 'include' });
          const data = await res.json();
          if (data && !data.error) {
            const fields: string[] = [];
            // Direct fields
            for (const f of data.direct || []) fields.push(f.field);
            // Related model fields
            for (const relFields of Object.values(data.related || {})) {
              for (const f of relFields as any[]) fields.push(f.field);
            }
            // JSON paths
            for (const f of data.json_paths || []) fields.push(f.field);
            // Line fields
            for (const f of data.lines || []) fields.push(f.field);

            if (fields.length > 0) {
              template = { ...template, columns: fields };
            }
          }
        } catch { /* proceed with existing columns */ }
      }

      const { Designer } = await import("@pdfme/ui");
      designerInstance.current = new Designer({
        domContainer: designerRef.current!,
        template: template as any,
      });
    };

    init();

    return () => {
      if (designerInstance.current) {
        designerInstance.current.destroy();
        designerInstance.current = null;
      }
    };
  }, [report, model]);

  const handleSubmit = async () => {
    if (!designerInstance.current) return;

    const template = designerInstance.current.getTemplate();
    const content = JSON.stringify(template);

    setSubmitting(true);
    setMessage(null);

    try {
      await apiClient.post("/wcapi/save/", {
        model_name: "alice_observation",
        data: {
          source: "pdf_designer",
          type: "template_submission",
          content,
          submitted_by: user?.id,
          notes,
        },
      });
      setMessage({ type: "success", text: "PDF template submitted to library successfully." });
      setNotes("");
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col h-full dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">PDF Template Designer</h1>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Submitting..." : "Submit to Library"}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-sm ${message.type === "success" ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"}`}>
          {message.text}
        </div>
      )}

      {/* Designer canvas */}
      <div ref={designerRef} className="flex-1 overflow-hidden" />
    </div>
  );
};

export default PdfDesigner;
