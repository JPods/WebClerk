/**
 * DefaultsConsole — every model's defaults in one grid (readme 106 A; Bill, 2026-11-07: "a
 * default.console where all such defaults can be seen compared and aligned").
 *
 * Storage is per model: each row is a model's own wc:model Setting, config.defaults =
 * {fields, formatting, features}. A feature is a switch a model has (line_contacts on a quote,
 * order and invoice; Bill, 2026-11-12): a tick box in the row of each model that has it. Comparison is here: models down, fields across; a shared field whose
 * value differs between the models that have it is marked. A cell saves through the door into
 * that model's Setting (the gate refuses a field the model lacks or a value off its list, with
 * coaching), and the row reloads what the server kept. The console's own wc:console Setting
 * ('defaults', apps/core/consoles.py) names the models, the shared fields and the formatting keys.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import { getRecords, saveRecord } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { refusalMessage } from '@/hooks/useRecordForm';

export interface DefaultsRow {
  model: string;
  settingId: number;
  version: number;
  fields: Record<string, unknown>;
  formatting: Record<string, unknown>;
  /** The model's switches (config.defaults.features); a model without a switch has no key. */
  features?: Record<string, boolean>;
  lists: Record<string, { value: string; label?: string }[]>;
}

/** The models whose value for `field` is not the one most models share: those cells are marked.
 *  A model without the field (no value and no list) is not compared. */
export function disagreements(rows: DefaultsRow[], field: string): Set<string> {
  const present = rows.filter((r) => r.fields[field] !== undefined && r.fields[field] !== '');
  if (present.length < 2) return new Set();
  const counts = new Map<string, number>();
  for (const r of present) counts.set(String(r.fields[field]), (counts.get(String(r.fields[field])) || 0) + 1);
  const [majority] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  if (counts.size === 1) return new Set();
  return new Set(present.filter((r) => String(r.fields[field]) !== majority).map((r) => r.model));
}

/** Every switch any model has, in the order first met. */
export function featuresOf(rows: DefaultsRow[]): string[] {
  const out: string[] = [];
  for (const r of rows) for (const k of Object.keys(r.features || {})) if (!out.includes(k)) out.push(k);
  return out;
}

/** The columns: the shared fields first, then every other field any model names, then formatting. */
export function columnsOf(rows: DefaultsRow[], shared: string[]): string[] {
  const seen = new Set(shared);
  const out = [...shared];
  for (const r of rows) for (const k of Object.keys(r.fields)) if (!seen.has(k)) { seen.add(k); out.push(k); }
  return out;
}

const cell: React.CSSProperties = { padding: '2px 6px', border: '1px solid var(--db-border, #d1d5db)', minWidth: 90 };
const input: React.CSSProperties = { width: '100%', font: 'inherit', background: 'transparent', color: 'inherit', border: 'none', outline: 'none' };

const DefaultsConsole: React.FC = () => {
  const dispatch = useDispatch();
  const [consoleDef, setConsole] = useState<{ models: string[]; shared: string[]; formatting: string[] } | null>(null);
  const [rows, setRows] = useState<DefaultsRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});   // "model|block|field" → typed value

  const load = useCallback(async () => {
    try {
      const consoles: any = await getRecords('setting', { purpose: 'wc:console', ida: 'defaults', limit: 1 });
      const def = consoles?.results?.[0]?.config;
      if (!def) { setError('No defaults console in this installation — a staff member runs: manage.py seed_consoles'); return; }
      setConsole({ models: def.models || [], shared: def.shared || [], formatting: def.formatting || [] });
      const defs: any = await getRecords('setting', { purpose: 'wc:model', limit: 200 });
      const byModel = new Map<string, any>((defs?.results || []).map((s: any) => [s.parent_model, s]));
      setRows((def.models || []).filter((m: string) => byModel.has(m)).map((m: string) => {
        const s = byModel.get(m);
        const d = s.config?.defaults || {};
        return { model: m, settingId: s.id, version: s.version, fields: d.fields || {}, formatting: d.formatting || {}, features: d.features || {}, lists: s.config?.selectlists || {} };
      }));
    } catch (e: any) { setError(`Could not read the definitions: ${e?.message || e}`); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const columns = useMemo(() => consoleDef ? columnsOf(rows, consoleDef.shared) : [], [rows, consoleDef]);
  const switches = useMemo(() => featuresOf(rows), [rows]);
  const marked = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const f of consoleDef?.shared || []) m.set(f, disagreements(rows, f));
    return m;
  }, [rows, consoleDef]);

  const save = useCallback(async (row: DefaultsRow, block: 'fields' | 'formatting', field: string, value: string) => {
    const current = String((row as any)[block][field] ?? '');
    if (value === current) return;
    const typed = block === 'formatting' && field === 'number_precision' ? Number(value) : value;
    try {
      await saveRecord('setting', { id: row.settingId, version: row.version, config: { defaults: { [block]: { [field]: typed } } } });
      dispatch(showToast({ message: `${row.model} ${field} = ${value || '(none)'}`, type: 'success' }));
    } catch (err: any) {
      dispatch(showToast({ message: `Not saved: ${refusalMessage(err)}`, type: 'error' }));
    }
    load();
  }, [dispatch, load]);

  const saveSwitch = useCallback(async (row: DefaultsRow, name: string, on: boolean) => {
    try {
      await saveRecord('setting', { id: row.settingId, version: row.version, config: { defaults: { features: { [name]: on } } } });
      dispatch(showToast({ message: `${row.model} ${name.replace(/_/g, ' ')} turned ${on ? 'on' : 'off'}`, type: 'success' }));
    } catch (err: any) {
      dispatch(showToast({ message: `Not saved: ${refusalMessage(err)}`, type: 'error' }));
    }
    load();
  }, [dispatch, load]);

  if (error) return <div style={{ padding: 16, color: 'var(--db-accent-red, #dc3545)' }}>{error}</div>;
  if (!consoleDef) return <div style={{ padding: 16 }}>Loading defaults…</div>;
  const key = (r: DefaultsRow, b: string, f: string) => `${r.model}|${b}|${f}`;
  return (
    <div style={{ padding: 16, overflow: 'auto' }}>
      <h2 style={{ fontWeight: 600, marginBottom: 4 }}>Defaults</h2>
      <p style={{ color: 'var(--db-text-dim, #6b7280)', marginBottom: 12, maxWidth: 820 }}>
        What a new record is born with when nobody says, and how each model formats. Each cell saves into
        that model's own definition; a marked cell differs from what most models share on that field.
      </p>
      <table style={{ borderCollapse: 'collapse', fontSize: 13 }} data-wc-defaults-console>
        <thead>
          <tr>
            <th style={cell}>model</th>
            {columns.map((c) => <th key={c} style={{ ...cell, fontWeight: 600 }}>{c}</th>)}
            {consoleDef.formatting.map((c) => <th key={c} style={{ ...cell, fontWeight: 600, color: 'var(--db-text-dim, #6b7280)' }}>{c}</th>)}
            {switches.map((c) => <th key={c} style={{ ...cell, fontWeight: 600 }} title="A switch: on or off for this model">{c.replace(/_/g, ' ')}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model}>
              <td style={{ ...cell, fontWeight: 600 }}>{r.model}</td>
              {columns.map((f) => {
                const bad = marked.get(f)?.has(r.model);
                const k = key(r, 'fields', f);
                const list = r.lists[f];
                const value = edits[k] ?? String(r.fields[f] ?? '');
                const style = { ...cell, background: bad ? 'var(--db-row-checked, #fef3c7)' : undefined };
                return (
                  <td key={f} style={style} title={bad ? 'Differs from what most models share' : undefined} data-marked={bad || undefined}>
                    {list && list.length ? (
                      <select style={input} value={value} onChange={(e) => save(r, 'fields', f, e.target.value)} aria-label={`${r.model} ${f}`}>
                        <option value="">—</option>
                        {list.map((o) => <option key={String(o.value)} value={String(o.value)}>{o.label || String(o.value)}</option>)}
                      </select>
                    ) : (
                      <input style={input} value={value} aria-label={`${r.model} ${f}`}
                        onChange={(e) => setEdits((p) => ({ ...p, [k]: e.target.value }))}
                        onBlur={(e) => { setEdits((p) => { const n = { ...p }; delete n[k]; return n; }); save(r, 'fields', f, e.target.value); }}
                        onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
                    )}
                  </td>
                );
              })}
              {consoleDef.formatting.map((f) => {
                const k = key(r, 'formatting', f);
                const value = edits[k] ?? String(r.formatting[f] ?? '');
                return (
                  <td key={f} style={{ ...cell, color: 'var(--db-text-dim, #6b7280)' }}>
                    <input style={input} value={value} aria-label={`${r.model} ${f}`}
                      onChange={(e) => setEdits((p) => ({ ...p, [k]: e.target.value }))}
                      onBlur={(e) => { setEdits((p) => { const n = { ...p }; delete n[k]; return n; }); save(r, 'formatting', f, e.target.value); }}
                      onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
                  </td>
                );
              })}
              {switches.map((name) => (
                <td key={name} style={{ ...cell, textAlign: 'center' }}>
                  {r.features && name in r.features ? (
                    <input type="checkbox" checked={r.features[name] === true} data-wc-switch={`${r.model}.${name}`}
                      aria-label={`${r.model} ${name.replace(/_/g, ' ')}`}
                      onChange={(e) => saveSwitch(r, name, e.target.checked)} />
                  ) : null}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DefaultsConsole;
