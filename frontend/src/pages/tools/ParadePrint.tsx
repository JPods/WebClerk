/**
 * ParadePrint — parade-print: every printed document with sample data, on the one parade page
 * (ParadeShell). Its stops are the prints by name, grouped by purpose; a stop shows the document
 * as it prints (Shift-click: the sample data behind it). Feedback stays on the Report.
 *
 * LastChecked: 2026-11-01 | WhereUsed: /parade-print | WhoCreated: Bill+Claude
 */
import { useEffect, useMemo, useState } from "react";
import apiClient from "../../api/axios";
import ParadeShell, { type Decision, type ParadeStop } from "./ParadeShell";

interface ParadeReport {
  id: number;
  name: string;
  target_model: string;
  category: string;
  has_sample_data: boolean;
  /** What the report can draw: a form layout, letter text, an operation, or nothing yet. */
  layout_kind?: "form" | "letter" | "operation" | "none";
  feedback: { choice: Decision; notes: string } | null;
}

interface ParadeManifest {
  groups: { name: string; description: string; reports: ParadeReport[] }[];
  total_reports: number;
}

const ParadePrint: React.FC = () => {
  const [manifest, setManifest] = useState<ParadeManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The preview HTML is fetched, not framed by URL: the access token is a Bearer
  // header held in JS, so an iframe src request carries no auth and gets a 401.
  const [preview, setPreview] = useState<{ key: string; html?: string; error?: string; loading: boolean; raw: boolean } | null>(null);

  useEffect(() => {
    apiClient.get("/wcapi/_parade_manifest/")
      .then((res) => setManifest(res.data?.data ?? res.data))
      .catch((err) => setError(err?.response?.data?.detail ?? "Failed to load the prints"));
  }, []);

  const stops = useMemo<ParadeStop[]>(() => (manifest?.groups ?? []).flatMap((g) => g.reports.map((r) => ({
    key: String(r.id),
    name: r.name,
    group: g.name,
    sub: `${r.target_model}  ${r.category}`,
    dot: !r.has_sample_data ? "gray" : r.layout_kind === "form" || r.layout_kind === "letter" ? "green" : "amber",
    title: r.has_sample_data ? "Click for the document · Shift-click for the sample data" : "No sample data",
    feedback: r.feedback ? { decision: r.feedback.choice, notes: r.feedback.notes } : null,
  }))), [manifest]);

  const load = async (stop: ParadeStop, raw: boolean) => {
    setPreview({ key: stop.key, loading: true, raw });
    try {
      const { data } = await apiClient.get("/wcapi/_parade_preview/", {
        params: raw ? { report_id: stop.key, raw: 1 } : { report_id: stop.key },
        responseType: "text",
        transformResponse: [(body) => body],
      });
      setPreview({ key: stop.key, loading: false, raw, html: typeof data === "string" ? data : JSON.stringify(data) });
    } catch (err: any) {
      const detail = err?.response?.data?.error?.details ?? err?.response?.data?.message ?? err?.message ?? "Preview failed";
      setPreview({ key: stop.key, loading: false, raw, error: String(detail) });
    }
  };

  const newTab = () => {
    if (!preview?.html) return;
    const url = URL.createObjectURL(new Blob([preview.html], { type: "text/html" }));
    window.open(url, "_blank");
    // Let the new tab load before the blob is released.
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  const btn = "px-2.5 py-1 text-xs font-medium transition-colors";
  return (
    <ParadeShell
      title="Parade: Print"
      description="Every printed document with sample data"
      noun="prints"
      stops={stops}
      groups={manifest?.groups.map((g) => ({ name: g.name, description: g.description }))}
      loading={!manifest && !error}
      error={error}
      emptyHint="A green dot has sample data to print"
      onSelect={(stop, alt) => load(stop, alt)}
      onFeedback={async (stop, fb) => {
        await apiClient.post("/wcapi/_parade_feedback/", { report_id: Number(stop.key), feedback: fb.decision, notes: fb.notes });
      }}
      toolbar={(stop) => (
        <>
          <div className="inline-flex rounded overflow-hidden border border-gray-300">
            <button onClick={() => load(stop, false)} title="The document as it prints"
              className={`${btn} ${preview?.raw ? "bg-white text-gray-600 hover:bg-gray-100" : "bg-gray-700 text-white"}`}>Document</button>
            <button onClick={() => load(stop, true)} title="The sample data behind it — same as Shift-click in the list"
              className={`${btn} ${preview?.raw ? "bg-gray-700 text-white" : "bg-white text-gray-600 hover:bg-gray-100"}`}>JSON</button>
          </div>
          <button onClick={() => document.querySelector<HTMLIFrameElement>('iframe[title^="Preview:"]')?.contentWindow?.print()}
            className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100">Print Preview</button>
          <button onClick={newTab}
            className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100">New Tab</button>
        </>
      )}
      renderStop={(stop) => (
        !preview || preview.key !== stop.key || preview.loading
          ? <div className="flex items-center justify-center h-full text-gray-400">Loading preview…</div>
          : preview.error
            ? <div className="flex items-center justify-center h-full text-red-600 text-center">
                <div><p className="text-lg mb-2">Preview failed</p><p className="text-sm">{preview.error}</p></div></div>
            : <iframe srcDoc={preview.html} className="w-full h-full border-0" title={`Preview: ${stop.name}`} />
      )}
    />
  );
};

export default ParadePrint;
