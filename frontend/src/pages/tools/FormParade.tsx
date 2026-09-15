/**
 * FormParade -- Form Review Parade page.
 *
 * Left-right split: grouped report list on the left, iframe preview on the right,
 * feedback bar at the bottom. Lets users review all 14 print forms with sample data
 * and record Keep / Modify / Don't Need feedback.
 *
 * LastChecked: 2026-08-16 | WhereUsed: /form-parade | WhoCreated: Bill+Claude
 */
import { useEffect, useState } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ReportFeedback {
  choice: "keep" | "modify" | "dont_need";
  notes: string;
}

interface ParadeReport {
  id: number;
  name: string;
  model_name: string;
  category: string;
  has_sample_data: boolean;
  render_url: string;
  feedback: ReportFeedback | null;
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
  feedback_options: string[];
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

const FormParade: React.FC = () => {
  const [manifest, setManifest] = useState<ParadeManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ParadeReport | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<number, ReportFeedback>>({});
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  /* Fetch manifest on mount */
  useEffect(() => {
    apiClient
      .get("/wcapi/_parade_manifest/")
      .then((res) => {
        const data: ParadeManifest = res.data?.data ?? res.data;
        setManifest(data);

        // Seed feedbackMap from any existing feedback on reports
        const initial: Record<number, ReportFeedback> = {};
        for (const g of data.groups) {
          for (const r of g.reports) {
            if (r.feedback) initial[r.id] = r.feedback;
          }
        }
        setFeedbackMap(initial);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail ?? "Failed to load manifest");
      })
      .finally(() => setLoading(false));
  }, []);

  /* When a report is selected, build the preview URL */
  const handleSelectReport = (report: ParadeReport) => {
    if (!report.has_sample_data) return;
    setSelectedReport(report);
    setNotes(feedbackMap[report.id]?.notes ?? "");
    setPreviewUrl(`/wcapi/_parade_preview/?report_id=${report.id}`);
  };

  /* Submit feedback */
  const handleFeedback = async (choice: ReportFeedback["choice"]) => {
    if (!selectedReport) return;
    setSaving(true);
    try {
      await apiClient.post("/wcapi/_parade_feedback/", {
        report_id: selectedReport.id,
        feedback: choice,
        notes,
      });
      setFeedbackMap((prev) => ({
        ...prev,
        [selectedReport.id]: { choice, notes },
      }));
    } catch (err: any) {
      console.error("Feedback save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  /* Print / open in new tab */
  const handlePrint = () => {
    if (!previewUrl) return;
    window.open(previewUrl, "_blank");
  };

  /* Feedback badge color */
  const feedbackColor = (choice: string) => {
    switch (choice) {
      case "keep":
        return "bg-green-500";
      case "modify":
        return "bg-amber-500";
      case "dont_need":
        return "bg-gray-400";
      default:
        return "bg-gray-300";
    }
  };

  const feedbackLabel = (choice: string) => {
    switch (choice) {
      case "keep":
        return "Keep";
      case "modify":
        return "Modify";
      case "dont_need":
        return "Don't Need";
      default:
        return choice;
    }
  };

  /* Current feedback for selected report */
  const currentFeedback = selectedReport ? feedbackMap[selectedReport.id] : null;

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500 text-lg">Loading form manifest...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-red-600 text-lg">{error}</p>
      </div>
    );
  }

  return (
    <>
      <PageMeta title="Form Review" description="Review print forms with sample data" />

      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="bg-gray-800 text-white px-6 py-3 flex items-center justify-between shrink-0">
          <h1 className="text-lg font-semibold">Form Review</h1>
          {manifest && (
            <span className="text-gray-300 text-sm">
              {manifest.total_reports} reports
              {" | "}
              {Object.keys(feedbackMap).length} reviewed
            </span>
          )}
        </div>

        {/* Main content — left/right split */}
        <div className="flex flex-1 min-h-0">
          {/* Left panel — report list */}
          <div className="w-[300px] shrink-0 bg-gray-50 border-r border-gray-200 overflow-y-auto">
            {manifest?.groups.map((group) => (
              <div key={group.name}>
                {/* Group header */}
                <div className="px-4 pt-4 pb-1">
                  <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wide">
                    {group.name}
                  </h2>
                  {group.description && (
                    <p className="text-xs text-gray-500 mt-0.5">{group.description}</p>
                  )}
                </div>

                {/* Report cards */}
                {group.reports.map((report) => {
                  const fb = feedbackMap[report.id];
                  const isSelected = selectedReport?.id === report.id;
                  const disabled = !report.has_sample_data;

                  return (
                    <button
                      key={report.id}
                      onClick={() => handleSelectReport(report)}
                      disabled={disabled}
                      title={disabled ? "No sample data available" : report.name}
                      className={`
                        w-full text-left px-4 py-2.5 border-b border-gray-100
                        transition-colors
                        ${isSelected ? "bg-blue-50 border-l-3 border-l-blue-500" : ""}
                        ${disabled ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-100 cursor-pointer"}
                      `}
                    >
                      <div className="flex items-center gap-2">
                        {/* Sample data dot */}
                        <span
                          className={`
                            inline-block w-2 h-2 rounded-full shrink-0
                            ${report.has_sample_data ? "bg-green-500" : "bg-gray-300"}
                          `}
                        />
                        <span className="text-sm font-medium text-gray-800 truncate">
                          {report.name}
                        </span>
                        {/* Feedback checkmark */}
                        {fb && (
                          <span
                            className={`ml-auto inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-xs shrink-0 ${feedbackColor(fb.choice)}`}
                            title={feedbackLabel(fb.choice)}
                          >
                            &#10003;
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2 mt-0.5 ml-4">
                        <span className="text-xs text-gray-500">{report.model_name}</span>
                        <span className="text-xs text-gray-400">{report.category}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Right panel — toolbar + preview */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Top toolbar */}
            {selectedReport && (
              <div className="shrink-0 border-b border-gray-300 bg-gray-50 px-4 py-2.5">
                <div className="flex items-center gap-3 flex-wrap">
                  {/* Report name */}
                  <span className="text-sm font-semibold text-gray-700">
                    {selectedReport.name}
                  </span>

                  {/* Divider */}
                  <div className="w-px h-5 bg-gray-300" />

                  {/* Feedback buttons */}
                  <button
                    onClick={() => handleFeedback("keep")}
                    disabled={saving}
                    className={`
                      px-3 py-1 rounded text-sm font-medium transition-colors
                      ${currentFeedback?.choice === "keep"
                        ? "bg-green-600 text-white ring-2 ring-green-300"
                        : "bg-green-500 text-white hover:bg-green-600"
                      }
                    `}
                  >
                    Keep
                  </button>
                  <button
                    onClick={() => handleFeedback("modify")}
                    disabled={saving}
                    className={`
                      px-3 py-1 rounded text-sm font-medium transition-colors
                      ${currentFeedback?.choice === "modify"
                        ? "bg-amber-600 text-white ring-2 ring-amber-300"
                        : "bg-amber-500 text-white hover:bg-amber-600"
                      }
                    `}
                  >
                    Modify
                  </button>
                  <button
                    onClick={() => handleFeedback("dont_need")}
                    disabled={saving}
                    className={`
                      px-3 py-1 rounded text-sm font-medium transition-colors
                      ${currentFeedback?.choice === "dont_need"
                        ? "bg-gray-500 text-white ring-2 ring-gray-300"
                        : "bg-gray-400 text-white hover:bg-gray-500"
                      }
                    `}
                  >
                    Don't Need
                  </button>

                  {/* Divider */}
                  <div className="w-px h-5 bg-gray-300" />

                  {/* Notes input */}
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Notes..."
                    className="flex-1 min-w-[150px] px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />

                  {/* Print preview — opens in iframe print dialog */}
                  <button
                    onClick={() => {
                      const iframe = document.querySelector<HTMLIFrameElement>('iframe[title^="Preview:"]');
                      iframe?.contentWindow?.print();
                    }}
                    className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    Print Preview
                  </button>

                  {/* Open in new tab */}
                  <button
                    onClick={handlePrint}
                    className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    New Tab
                  </button>

                  {/* Status */}
                  {currentFeedback && (
                    <span className="text-xs text-gray-500 italic">
                      {feedbackLabel(currentFeedback.choice)}
                    </span>
                  )}
                  {saving && (
                    <span className="text-xs text-blue-500">Saving...</span>
                  )}
                </div>
              </div>
            )}

            {/* Preview area */}
            <div className="flex-1 min-h-0 bg-white">
              {previewUrl ? (
                <iframe
                  src={previewUrl}
                  className="w-full h-full border-0"
                  title={`Preview: ${selectedReport?.name ?? ""}`}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <p className="text-lg mb-2">Select a report to preview</p>
                    <p className="text-sm">
                      Click any report with a green dot in the left panel
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default FormParade;
