/**
 * ParadeForm — parade-form: each model's form, one stop per model (Bill, 2026-11-01: "parade-form
 * ... walk through each model's form with option to flip to detail"). The stop is the real list page
 * in a frame with the model's first record open — the form users get, untouched. Staff flip it to
 * Detail (the field grid, db.detail — staff only, an always rule) with ?view=; the saved View choice
 * is not changed. Feedback lands on the model's definition (services/parade.py), beside parade-list's.
 *
 * LastChecked: 2026-11-01 | WhereUsed: /parade-form | WhoCreated: Bill+Claude
 */
import { useEffect, useMemo, useState } from "react";
import apiClient from "../../api/axios";
import { getModelNames, getRecords } from "@/api/wcapi";
import { useAppSelector } from "../../store/hooks";
import { isStaffUser, type DetailViewPref } from "../../layout/MacTopBar";
import ParadeShell, { type Feedback, type ParadeStop } from "./ParadeShell";

interface ModelEntry { name: string; app: string; kind: string; label: string }
interface Definition { id: number; feedback: Feedback | null }

/** What to look at on each form, said once. */
const CHECKS = [
  "Is what you look for first at the top? Are the fields a business user needs there, and nothing else?",
  "Labels read as words, numbers align right, dates are local; money and quantities show positive.",
  "Type in a field and save: it saves green, or red with the reason.",
  "Lines and related records (tabs, panels) open and read like the lists do.",
];

const ParadeForm: React.FC = () => {
  const { user } = useAppSelector((state) => state.auth);
  const isStaff = isStaffUser(user);
  const [models, setModels] = useState<ModelEntry[] | null>(null);
  const [defs, setDefs] = useState<Record<string, Definition>>({});
  const [error, setError] = useState<string | null>(null);
  // The record each stop opens: its list's first, fetched when the stop is chosen; null = none.
  const [firstId, setFirstId] = useState<Record<string, number | null>>({});
  const [view, setView] = useState<DetailViewPref>("form");

  useEffect(() => {
    getModelNames()
      .then((d: any) => setModels(d?.models ?? d?.data?.models ?? []))
      .catch(() => setError("Could not read the models"));
    getRecords("setting", { purpose: "wc:model", limit: 500 })
      .then((r: any) => setDefs(Object.fromEntries((r?.results ?? []).map((s: any) => {
        const fb = s.prefs?.parades?.form;
        return [s.parent_model, { id: s.id, feedback: fb ? { decision: fb.decision, notes: fb.notes ?? "" } : null }];
      }))))
      .catch(() => setDefs({}));
  }, []);

  const stops = useMemo<ParadeStop[]>(() => (models ?? []).map((m) => ({
    key: m.name,
    name: m.name,
    group: m.app,
    sub: m.kind === "line" ? "lines" : m.kind === "header" ? "documents" : undefined,
    dot: firstId[m.name] === null ? "gray" : defs[m.name] ? "green" : "amber",
    title: firstId[m.name] === null ? "No records to show a form for" : defs[m.name] ? `${m.label}: the form` : "No model definition yet",
    feedback: defs[m.name]?.feedback ?? null,
  })), [models, defs, firstId]);

  const src = (model: string, id: number) => `/${model}?id=${id}${isStaff ? `&view=${view}` : ""}`;
  const btn = "px-2.5 py-1 text-xs font-medium transition-colors";

  return (
    <ParadeShell
      title="Parade: Form"
      description="Each model's form, one at a time"
      noun="models"
      stops={stops}
      groupFilter="App"
      loading={!models && !error}
      error={error}
      emptyHint="Each model's form on its first record — mark it Keep, Modify or Don't Need"
      onSelect={(stop) => {
        if (stop.key in firstId) return;
        getRecords(stop.key, { limit: 1 })
          .then((r: any) => setFirstId((f) => ({ ...f, [stop.key]: r?.results?.[0]?.id ?? null })))
          .catch(() => setFirstId((f) => ({ ...f, [stop.key]: null })));
      }}
      onFeedback={async (stop, fb) => {
        const def = defs[stop.key];
        if (!def) throw new Error("This model has no definition to keep the feedback on");
        await apiClient.post(`/wcapi/setting/${def.id}/parade_feedback/`, { parade: "form", decision: fb.decision, notes: fb.notes });
      }}
      toolbar={(stop) => (
        <>
          {isStaff && (
            <div className="inline-flex rounded overflow-hidden border border-gray-300">
              {(["form", "detail"] as DetailViewPref[]).map((v) => (
                <button key={v} onClick={() => setView(v)}
                  title={v === "form" ? "The business form (db.form)" : "Every field, the grid (db.detail) — staff only"}
                  className={`${btn} ${view === v ? "bg-gray-700 text-white" : "bg-white text-gray-600 hover:bg-gray-100"}`}>
                  {v === "form" ? "Form" : "Detail"}
                </button>
              ))}
            </div>
          )}
          {firstId[stop.key] != null && (
            <button onClick={() => window.open(src(stop.key, firstId[stop.key]!), `parade-form-${stop.key}`, "popup,width=1400,height=900")}
              className="px-3 py-1 rounded text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
              title="The form in a window of its own">Open ↗</button>
          )}
        </>
      )}
      renderStop={(stop) => {
        const id = firstId[stop.key];
        if (id === undefined) return <div className="flex items-center justify-center h-full text-gray-400">Finding a record…</div>;
        if (id === null) return <div className="flex items-center justify-center h-full text-gray-400">No {stop.name} records — nothing to show a form for</div>;
        return (
          <div className="flex flex-col h-full">
            <ul className="shrink-0 px-4 py-2 text-xs text-gray-600 bg-gray-50 border-b border-gray-200 list-disc pl-8">
              {CHECKS.map((c) => <li key={c}>{c}</li>)}
            </ul>
            <iframe key={`${stop.key}:${view}`} src={src(stop.key, id)} title={`Form: ${stop.name}`} className="flex-1 w-full border-0" />
          </div>
        );
      }}
    />
  );
};

export default ParadeForm;
