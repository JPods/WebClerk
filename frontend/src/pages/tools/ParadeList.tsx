/**
 * ParadeList — parade-list: each model's list, one stop per model (Bill, 2026-11-01: "parade-list
 * (walk through each model's list form)"; models alphabetical, grouped by app, a parade can be one
 * app). The stop is the real list page in a frame — the page itself, untouched, so the parade tests
 * what users get: columns, order, Σ, click/double-click, edit in list. "Open" gives it a window.
 * Feedback lands on the model's definition (services/parade.py) until plan 100 moves notes to
 * Actions.
 *
 * LastChecked: 2026-11-01 | WhereUsed: /parade-list | WhoCreated: Bill+Claude
 */
import { useEffect, useMemo, useState } from "react";
import apiClient from "../../api/axios";
import { getModelNames, getRecords } from "@/api/wcapi";
import ParadeShell, { type Feedback, type ParadeStop } from "./ParadeShell";

interface ModelEntry { name: string; app: string; kind: string; label: string }
interface Definition { id: number; feedback: Feedback | null }

/** What to look at on each list — the WC List Standard and the list rules, said once. */
const CHECKS = [
  "Columns: is the first one the one you look for? Hide, add, reorder and size them (≡).",
  "Order: unclicked, the list reads by its orderby, else sequence, else newest. Click a column to sort.",
  "Click selects, Shift-click a range, Cmd-click one more; double-click opens the record.",
  "Subset / Omit: the Σ row follows the rows shown; prices and rates have no Σ.",
  "Edit in list (if offered): a plain value saves green, or red with the reason.",
];

const ParadeList: React.FC = () => {
  const [models, setModels] = useState<ModelEntry[] | null>(null);
  const [defs, setDefs] = useState<Record<string, Definition>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModelNames()
      .then((d: any) => setModels(d?.models ?? d?.data?.models ?? []))
      .catch(() => setError("Could not read the models"));
    getRecords("setting", { purpose: "wc:model", limit: 500 })
      .then((r: any) => setDefs(Object.fromEntries((r?.results ?? []).map((s: any) => {
        const fb = s.prefs?.parades?.list;
        return [s.parent_model, { id: s.id, feedback: fb ? { decision: fb.decision, notes: fb.notes ?? "" } : null }];
      }))))
      .catch(() => setDefs({}));
  }, []);

  const stops = useMemo<ParadeStop[]>(() => (models ?? []).map((m) => ({
    key: m.name,
    name: m.name,
    group: m.app,
    sub: m.kind === "line" ? "lines" : m.kind === "header" ? "documents" : undefined,
    dot: defs[m.name] ? "green" : "amber",
    title: defs[m.name] ? `${m.label}: the list` : "No model definition yet",
    feedback: defs[m.name]?.feedback ?? null,
  })), [models, defs]);

  return (
    <ParadeShell
      title="Parade: List"
      description="Each model's list, one at a time"
      noun="models"
      stops={stops}
      groupFilter="App"
      loading={!models && !error}
      error={error}
      emptyHint="Each model's list as users see it — mark it Keep, Modify or Don't Need"
      onFeedback={async (stop, fb) => {
        const def = defs[stop.key];
        if (!def) throw new Error("This model has no definition to keep the feedback on");
        await apiClient.post(`/wcapi/setting/${def.id}/parade_feedback/`, { parade: "list", decision: fb.decision, notes: fb.notes });
      }}
      toolbar={(stop) => (
        <button onClick={() => window.open(`/${stop.key}`, `parade-list-${stop.key}`, "popup,width=1400,height=900")}
          className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
          title="The list in a window of its own">Open ↗</button>
      )}
      renderStop={(stop) => (
        <div className="flex flex-col h-full">
          <ul className="shrink-0 px-4 py-2 text-xs text-gray-600 bg-gray-50 border-b border-gray-200 list-disc pl-8">
            {CHECKS.map((c) => <li key={c}>{c}</li>)}
          </ul>
          <iframe key={stop.key} src={`/${stop.key}`} title={`List: ${stop.name}`} className="flex-1 w-full border-0" />
        </div>
      )}
    />
  );
};

export default ParadeList;
