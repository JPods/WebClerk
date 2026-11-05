/**
 * LookupWidget — a foreign key found by search. Shows the record's name; typing searches
 * the model; a miss offers to add the typed name through the door.
 *
 * A lookup stored by ida (terms) is a code list: a dozen records a person picks from a
 * select, never searches (Bill, 2026-11-05). The list is the model's active records.
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import type { WidgetProps } from "./types";
import { getRecord, getRecords } from "@/api/wcapi";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";
/** A name as text: an i18n object ({en: "..."}) gives its first string, never "[object Object]". */
export const asText = (v: any): string =>
  typeof v === "string" ? v
  : v && typeof v === "object" && !Array.isArray(v) ? String(Object.values(v).find(x => typeof x === "string") ?? "")
  : v == null ? "" : String(v);
/** The found record's name: what the behavior names (display), else the first of display_name,
 *  attention (a contact), name, company, email, ida — never a bare id while a word exists. */
export const nameOf = (rec: any, display?: string): string =>
  (display ? asText(rec?.[display]) : "")
  || asText(rec?.display_name) || asText(rec?.attention) || asText(rec?.name) || asText(rec?.company)
  || asText(rec?.email) || asText(rec?.ida) || (rec?.id ? `#${rec.id}` : "");   // a document is its ida; its company snapshot comes after

export const LookupWidget: React.FC<WidgetProps> = ({ name, value: v, onChange, disabled, model = "", valueField = "id", displayField, className, mode }) => {
  const shown = (rec: any) => nameOf(rec, displayField);
  const [query, setQuery] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const isList = valueField === "ida";
  const [list, setList] = useState<any[]>([]);

  // A code list: every active record of the model, once
  useEffect(() => {
    if (!isList || !model) return;
    getRecords(model, { limit: 200 }).then((res: any) => setList((res?.results || []).filter((r: any) => r.is_active !== false)))
      .catch(() => setList([]));
  }, [isList, model]);

  // The name behind the value, on mount or when it changes: by id, or by ida (a term)
  useEffect(() => {
    if (!v) { setDisplayName(""); return; }
    if (typeof v === "object") { setDisplayName(shown(v)); return; }
    if (valueField === "ida") {
      getRecords(model, { ida: String(v), limit: 1 }).then((res: any) => { const rec = res?.results?.[0]; setDisplayName(rec ? shown(rec) : String(v)); }).catch(() => setDisplayName(String(v)));
      return;
    }
    getRecord(model, Number(v)).then((res: any) => { if (res?.record) setDisplayName(shown(res.record)); }).catch(() => {});
  }, [v, model, valueField]);

  const doSearch = useCallback((q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setLoading(true);
    getRecords(model, { keyword: q, limit: 10 }).then((res: any) => { setResults(res?.results || []); setOpen(true); })
      .catch(() => setResults([])).finally(() => setLoading(false));
  }, [model]);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q); setDisplayName(""); onChange(null);   // the FK clears until they pick
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(q), 250);
  };
  const handleSelect = (rec: any) => { onChange(valueField === "ida" ? rec.ida : rec.id); setDisplayName(shown(rec)); setQuery(""); setOpen(false); };
  const handleAddNew = async () => {
    try {
      const { createRecord } = await import("@/api/wcapi");
      // The typed text is the new record's name; everything else is the server's.
      const values: Record<string, any> = {};
      if (model === "contact") {
        const parts = query.trim().split(/\s+/);
        values.name_first = parts[0] || query; values.name_last = parts.slice(1).join(" ") || "";
      } else values.name = query;
      const result = await createRecord(model, values) as any;
      if (result?.id) handleSelect({ ...(result.record || {}), id: result.id });
    } catch (err) { console.error("[LookupWidget] add new failed:", err); }
  };
  useEffect(() => {
    const handler = (e: MouseEvent) => { if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (mode === "print") return <span className="text-[inherit]">{displayName || (v ? (valueField === "ida" ? String(v) : `#${v}`) : "—")}</span>;
  if (isList) {
    const current = v == null ? "" : String(v);
    return (
      <select name={name} className={className || s} value={current} disabled={disabled}
        onChange={e => onChange(e.target.value || null)}>
        <option value="">--</option>
        {list.map(r => <option key={r.ida} value={r.ida}>{shown(r)}</option>)}
        {current && !list.some(r => r.ida === current) && <option value={current}>{current}</option>}
      </select>
    );
  }
  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      <input name={name} className={className || s} value={displayName || query}
        onChange={handleInput}
        onFocus={() => { if (displayName) { setQuery(displayName); setDisplayName(""); } }}
        placeholder={`search ${model}...`} disabled={disabled} />
      {open && (results.length > 0 || (query.length >= 2 && !loading)) && (
        <div className="db-lookup-dropdown">
          {results.map(r => (
            <div key={r.id} className="db-lookup-option" onClick={() => handleSelect(r)}>
              <span className="db-lookup-name">{shown(r)}</span>
              {r.email && <span className="db-lookup-hint">{r.email}</span>}
            </div>
          ))}
          {results.length === 0 && <div className="db-lookup-empty">No matches</div>}
          <div className="db-lookup-add" onClick={handleAddNew}>+ Add "{query}"</div>
        </div>
      )}
    </div>
  );
};
