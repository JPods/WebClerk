/**
 * ParadeShell — the one parade page (Bill, 2026-11-01). Every parade is parade-<what it walks>:
 * parade-list (each model's list), parade-form (each model's form), parade-print (every printed
 * document), parade-console (each process console). They differ only in their stops and what one
 * stop shows; the page is this:
 *
 *   left   the stops, grouped (by app, by purpose), alphabetical in a group, each named by what it
 *          is (a model, a print, a console), with a group filter and its progress mark
 *   right  the stop's toolbar — Keep / Modify / Don't Need, a note, the parade's own buttons — and
 *          what the stop shows
 *
 * The parade supplies `stops`, `renderStop`, `onFeedback` and, if it has them, `toolbar` buttons.
 */
import React, { useMemo, useState } from "react";
import PageMeta from "@/components/common/PageMeta";

export type Decision = "keep" | "modify" | "dont_need";
export interface Feedback { decision: Decision; notes: string }

export interface ParadeStop {
  key: string;
  /** What the stop is: a model's name, a print's name, a console's name */
  name: string;
  group: string;
  /** A second line under the name (a print's model and category) */
  sub?: string;
  /** green: ready; amber: partly; gray: nothing to show (and not selectable) */
  dot?: "green" | "amber" | "gray";
  title?: string;
  feedback?: Feedback | null;
}

const DECISION_LABEL: Record<Decision, string> = { keep: "Keep", modify: "Modify", dont_need: "Don't Need" };
const DECISION_COLOR: Record<Decision, string> = { keep: "bg-green-500", modify: "bg-amber-500", dont_need: "bg-gray-400" };

export interface ParadeShellProps {
  title: string;
  description: string;
  /** "models", "prints", "consoles" — for the header count */
  noun: string;
  stops: ParadeStop[];
  /** Group order and their lines; groups not named here follow alphabetically */
  groups?: { name: string; description?: string }[];
  /** Offer a filter by group ("App: products") */
  groupFilter?: string;
  loading?: boolean;
  error?: string | null;
  emptyHint?: string;
  /** What the selected stop shows */
  renderStop: (stop: ParadeStop) => React.ReactNode;
  /** The parade's own toolbar buttons for the selected stop */
  toolbar?: (stop: ParadeStop) => React.ReactNode;
  /** A stop was chosen (a print fetches its preview; Shift-click passes `alt`) */
  onSelect?: (stop: ParadeStop, alt: boolean) => void;
  /** Keep / Modify / Don't Need with the note — the parade saves it where it keeps feedback */
  onFeedback: (stop: ParadeStop, feedback: Feedback) => Promise<void>;
}

const ParadeShell: React.FC<ParadeShellProps> = ({
  title, description, noun, stops, groups, groupFilter, loading, error, emptyHint,
  renderStop, toolbar, onSelect, onFeedback,
}) => {
  const [selected, setSelected] = useState<ParadeStop | null>(null);
  const [given, setGiven] = useState<Record<string, Feedback>>({});
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [only, setOnly] = useState("");

  const feedbackOf = (s: ParadeStop) => given[s.key] ?? s.feedback ?? null;

  // Groups in the parade's order, then the rest alphabetically; stops alphabetical within each.
  const grouped = useMemo(() => {
    const byGroup = new Map<string, ParadeStop[]>();
    stops.forEach((s) => { if (!byGroup.has(s.group)) byGroup.set(s.group, []); byGroup.get(s.group)!.push(s); });
    const named = (groups ?? []).map((g) => g.name).filter((n) => byGroup.has(n));
    const rest = [...byGroup.keys()].filter((n) => !named.includes(n)).sort();
    return [...named, ...rest]
      .filter((n) => !only || n === only)
      .map((n) => ({ name: n, description: groups?.find((g) => g.name === n)?.description,
                     stops: [...byGroup.get(n)!].sort((a, b) => a.name.localeCompare(b.name)) }));
  }, [stops, groups, only]);

  const reviewed = stops.filter((s) => feedbackOf(s)).length;

  const choose = (s: ParadeStop, alt: boolean) => {
    if (s.dot === "gray") return;
    setSelected(s);
    setNotes(feedbackOf(s)?.notes ?? "");
    onSelect?.(s, alt);
  };

  const decide = async (decision: Decision) => {
    if (!selected) return;
    setSaving(true);
    try {
      await onFeedback(selected, { decision, notes });
      setGiven((g) => ({ ...g, [selected.key]: { decision, notes } }));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-screen text-gray-500 text-lg">Loading {noun}…</div>;
  if (error) return <div className="flex items-center justify-center h-screen text-red-600 text-lg">{error}</div>;

  const current = selected ? feedbackOf(selected) : null;
  return (
    <>
      <PageMeta title={title} description={description} />
      <div className="flex flex-col h-screen">
        <div className="bg-gray-800 text-white px-6 py-3 flex items-center justify-between shrink-0">
          <h1 className="text-lg font-semibold">{title}</h1>
          <div className="flex items-center gap-3">
            {groupFilter && (
              <select value={only} onChange={(e) => setOnly(e.target.value)}
                className="text-sm text-gray-800 rounded px-2 py-0.5" title={`Walk one ${groupFilter.toLowerCase()} only`}>
                <option value="">{groupFilter}: all</option>
                {[...new Set(stops.map((s) => s.group))].sort().map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            )}
            <span className="text-gray-300 text-sm">{stops.length} {noun} | {reviewed} reviewed</span>
          </div>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* The stops */}
          <div className="w-[300px] shrink-0 bg-gray-50 border-r border-gray-200 overflow-y-auto">
            {grouped.map((g) => (
              <div key={g.name}>
                <div className="px-4 pt-4 pb-1">
                  <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wide">{g.name}</h2>
                  {g.description && <p className="text-xs text-gray-500 mt-0.5">{g.description}</p>}
                </div>
                {g.stops.map((s) => {
                  const fb = feedbackOf(s);
                  const disabled = s.dot === "gray";
                  return (
                    <button key={s.key} onClick={(e) => choose(s, e.shiftKey)} disabled={disabled} title={s.title}
                      className={`w-full text-left px-4 py-2.5 border-b border-gray-100 transition-colors
                        ${selected?.key === s.key ? "bg-blue-50 border-l-3 border-l-blue-500" : ""}
                        ${disabled ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-100 cursor-pointer"}`}>
                      <div className="flex items-center gap-2">
                        <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${
                          s.dot === "gray" ? "bg-gray-300" : s.dot === "amber" ? "bg-amber-400" : "bg-green-500"}`} />
                        <span className="text-sm font-medium text-gray-800 truncate">{s.name}</span>
                        {fb && (
                          <span className={`ml-auto inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-xs shrink-0 ${DECISION_COLOR[fb.decision]}`}
                            title={DECISION_LABEL[fb.decision]}>&#10003;</span>
                        )}
                      </div>
                      {s.sub && <div className="mt-0.5 ml-4 text-xs text-gray-500">{s.sub}</div>}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* The stop */}
          <div className="flex-1 flex flex-col min-w-0">
            {selected && (
              <div className="shrink-0 border-b border-gray-300 bg-gray-50 px-4 py-2.5">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm font-semibold text-gray-700">{selected.name}</span>
                  {toolbar?.(selected)}
                  <div className="w-px h-5 bg-gray-300" />
                  {(["keep", "modify", "dont_need"] as Decision[]).map((d) => (
                    <button key={d} onClick={() => decide(d)} disabled={saving}
                      className={`px-3 py-1 rounded text-sm font-medium text-white transition-colors ${DECISION_COLOR[d]} ${
                        current?.decision === d ? "ring-2 ring-offset-1 ring-gray-400" : "opacity-90 hover:opacity-100"}`}>
                      {DECISION_LABEL[d]}
                    </button>
                  ))}
                  <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes…"
                    className="flex-1 min-w-[150px] px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-400" />
                  {current && <span className="text-xs text-gray-500 italic">{DECISION_LABEL[current.decision]}</span>}
                  {saving && <span className="text-xs text-blue-500">Saving…</span>}
                </div>
              </div>
            )}
            <div className="flex-1 min-h-0 bg-white">
              {selected ? renderStop(selected) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <p className="text-lg mb-2">Choose one on the left</p>
                    {emptyHint && <p className="text-sm">{emptyHint}</p>}
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

export default ParadeShell;
