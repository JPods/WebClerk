/* WhereUsed: dbRoutes (workorder), protectedRoutesConfig (/transactions/work-order/detail/:id) | WhoCreated: Bill+Claude */
/**
 * WorkOrderWindow — the one place a workorder is made, counted, built and completed. Hand-built
 * (Bill, 2026-09-26: "Not use json forms in workorder").
 *
 * One item per line, signed (Bill, 2026-09-26):
 *   count workorder — count lines (what was counted; the server records the book) and adjust
 *     lines (a change with its reason). They move stock as they save; a recount posts the
 *     difference; a line that has moved stock is the record and is not deleted.
 *   production workorder — build (+), consume (−), scrap (−). Nothing moves until Complete, which
 *     builds deepest first and costs the made item from the layers its parts consumed. Expand fills
 *     the lines from the BOM, one level (editable) or the full BOM (locked from hand edits). One
 *     workorder per build.
 * Plan: ~/Allie/readmes/assessments/2026-09-26-workorder-window.md
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { getRecord, getRecords, searchItems } from '@/api/wcapi';
import {
  completeWorkorder, createWorkorder, expandWorkorder, lineBody, saveWorkorderLines,
} from '@/api/workorderApi';
import { showToast } from '@/store/slices/toastSlice';

type Kind = 'count' | 'production';
type LineType = 'count' | 'adjust' | 'build' | 'consume' | 'scrap';

interface SavedLine {
  id: number;
  line_type: LineType;
  item_fk_id?: number;
  item?: { item_id?: number; ida?: string; description?: string };
  quantity?: { active?: number; staged?: number };
  cost?: { unit?: number };
  refs?: { bom?: { parent_line_id?: number; role?: string }; bom_expand?: { depth?: number } };
  comments?: { process?: { mgs?: string; user?: string; time?: string }[] };
  events?: any[];
}

interface NewRow {
  key: string;
  item_id: number;
  ida: string;
  name: string;
  label: string;
  on_hand: number;
  line_type: LineType;
  qty: string;
  unit_cost: string;
  reason: string;
}

const SIGN: Record<LineType, string> = { count: '=', adjust: '±', build: '+', consume: '−', scrap: '−' };
const REASONS = ['damaged', 'found', 'lost', 'miscount', 'returned to vendor', 'sample', 'theft'];

const cell: React.CSSProperties = { padding: '4px 6px', borderBottom: '1px solid var(--db-border)', verticalAlign: 'top' };
const num: React.CSSProperties = { ...cell, textAlign: 'right', fontVariantNumeric: 'tabular-nums' };
const btn = 'rounded border px-2 py-1 text-xs disabled:opacity-40';

function itemLabel(l: SavedLine): string {
  const it = l.item || {};
  return [it.ida, it.description].filter(Boolean).join(' — ') || `item ${l.item_fk_id ?? it.item_id ?? ''}`;
}

function lastReason(l: SavedLine): string {
  const entries = l.comments?.process || [];
  return entries.length ? entries[entries.length - 1].mgs || '' : '';
}

function lastEvent(l: SavedLine): any {
  const events = (l.events || []).filter((e) => e && typeof e === 'object');
  return events.length ? events[events.length - 1] : null;
}

const money = (v: unknown) => (typeof v === 'number' ? v.toFixed(2) : v === undefined || v === null ? '' : String(v));

export default function WorkOrderWindow({ recordId: propId }: { modelName?: string; recordId?: number }) {
  const params = useParams();
  const dispatch = useDispatch();
  const [woId, setWoId] = useState<number>(propId || (params.id ? Number(params.id) : 0));
  const [wo, setWo] = useState<any>(null);
  const [lines, setLines] = useState<SavedLine[]>([]);
  const [rows, setRows] = useState<NewRow[]>([]);
  const [recount, setRecount] = useState<Record<number, string>>({});
  const [search, setSearch] = useState('');
  const [found, setFound] = useState<any[]>([]);
  const latestSearch = useRef('');
  const [busy, setBusy] = useState(false);

  const kind: Kind = wo?.kind === 'count' ? 'count' : 'production';
  const complete = wo?.status === 'complete';
  const fullBom = lines.some((l) => l.refs?.bom_expand?.depth === 0);
  const say = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    dispatch(showToast({ message, type }));
  }, [dispatch]);
  const fail = useCallback((e: any) => {
    say(e?.response?.data?.message || e?.message || 'That did not save.', 'error');
  }, [say]);

  const load = useCallback(async () => {
    if (!woId) return;
    const res: any = await getRecord('workorder', woId);
    setWo(res?.record || res);
    const got: any = await getRecords('workorder_line', { workorder_id: woId, limit: 500, order_by: 'line_number' });
    setLines((got?.results || got?.records || []) as SavedLine[]);
    setRows([]);
    setRecount({});
  }, [woId]);

  useEffect(() => { load().catch(fail); }, [load, fail]);

  // ── starting a workorder ────────────────────────────────────────────────────────────────
  const start = async (k: Kind) => {
    setBusy(true);
    try { setWoId(await createWorkorder(k)); } catch (e) { fail(e); }
    setBusy(false);
  };
  // A workorder made from the list (+ Add) arrives empty: it picks what it is before any line.
  const choose = async (k: Kind) => {
    setBusy(true);
    try { await saveWorkorderLines(woId, k, []); await load(); } catch (e) { fail(e); }
    setBusy(false);
  };

  // ── adding lines ────────────────────────────────────────────────────────────────────────
  const find = async (text: string) => {
    setSearch(text);
    latestSearch.current = text.trim();
    if (text.trim().length < 2) { setFound([]); return; }
    try {
      const q = text.trim();
      const res: any = await searchItems(q, { limit: 8 });
      let list: any[] = res?.results || res?.records || [];
      // A scanner's Enter takes the first match, so the exact code must be first — fetched
      // outright when the keyword search ranks it out of the list.
      const exact = (it: any) => [it.ida, it.sku].some((v) => String(v || '').toLowerCase() === q.toLowerCase());
      if (!list.some(exact)) {
        const direct: any = await getRecords('item', { ida: q, limit: 1 });
        list = [...(direct?.results || direct?.records || []), ...list];
      }
      // Each keystroke searches; only the answer to the latest one may land (a scanner types
      // faster than the answers come back, and an older answer arriving last would win).
      if (q !== latestSearch.current) return;
      setFound([...list.filter(exact), ...list.filter((it) => !exact(it))]);
    } catch { setFound([]); }
  };

  const add = (item: any, lineType?: LineType) => {
    const type: LineType = lineType || (kind === 'count' ? 'count' : lines.some((l) => l.line_type === 'build') || rows.some((r) => r.line_type === 'build') ? 'consume' : 'build');
    setRows((prev) => [...prev, {
      key: `${item.id}-${Date.now()}`, item_id: item.id, ida: item.ida || '', name: item.name || '',
      label: [item.ida, item.name].filter(Boolean).join(' — '),
      on_hand: Number(item.quantity?.on_hand || 0), line_type: type,
      qty: type === 'count' ? String(Number(item.quantity?.on_hand || 0)) : '', unit_cost: '', reason: '',
    }]);
    setSearch('');
    setFound([]);
  };

  const setRow = (key: string, patch: Partial<NewRow>) =>
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const signed = (r: NewRow): number => {
    const q = Number(r.qty || 0);
    return r.line_type === 'consume' || r.line_type === 'scrap' ? -Math.abs(q) : r.line_type === 'build' ? Math.abs(q) : q;
  };

  // ── saving ──────────────────────────────────────────────────────────────────────────────
  const save = async () => {
    const missing = rows.find((r) => r.line_type === 'adjust' && !r.reason.trim());
    if (missing) { say(`An adjustment needs its reason (${missing.label}).`, 'error'); return; }
    const body: Record<string, unknown>[] = rows.map((r, i) => lineBody({
      item_id: r.item_id, ida: r.ida, description: r.name, line_type: r.line_type as any, quantity: signed(r),
      unit_cost: r.unit_cost === '' ? undefined : Number(r.unit_cost),
      reason: r.reason || undefined,
    } as any, i));
    for (const [id, value] of Object.entries(recount)) {
      const line = lines.find((l) => l.id === Number(id));
      if (line && value !== '') body.push({ id: line.id, _dirty: true, quantity: { ...line.quantity, active: Number(value) } });
    }
    if (!body.length) return;
    setBusy(true);
    try {
      await saveWorkorderLines(woId, kind, body);
      say(kind === 'count' ? 'Saved: the stock is corrected.' : 'Saved. Nothing moves until Complete.');
      await load();
    } catch (e) { fail(e); }
    setBusy(false);
  };

  const remove = async (line: SavedLine) => {
    setBusy(true);
    try { await saveWorkorderLines(woId, kind, [{ id: line.id, _delete: true }]); await load(); } catch (e) { fail(e); }
    setBusy(false);
  };

  const expand = async (line: SavedLine, depth: 0 | 1) => {
    setBusy(true);
    try { await expandWorkorder(woId, line.id, depth); await load(); } catch (e) { fail(e); }
    setBusy(false);
  };

  const finish = async () => {
    if (!window.confirm('Complete this build? Every line moves its stock now, all or nothing, and the workorder closes.')) return;
    setBusy(true);
    try {
      const done: any = await completeWorkorder(woId);
      say(`Completed: ${done?.lines_applied ?? ''} lines applied.`);
      await load();
    } catch (e) { fail(e); }
    setBusy(false);
  };

  const depthOf = useMemo(() => {
    const byId = new Map(lines.map((l) => [l.id, l]));
    return (l: SavedLine) => {
      let d = 0; let p = l.refs?.bom?.parent_line_id;
      while (p && byId.has(p) && d < 10) { d += 1; p = byId.get(p)?.refs?.bom?.parent_line_id; }
      return d;
    };
  }, [lines]);

  // ── render ──────────────────────────────────────────────────────────────────────────────
  if (!woId) {
    return (
      <div className="p-4 space-y-3" style={{ fontSize: 13 }}>
        <h2 className="text-base font-semibold">New workorder</h2>
        <p className="db-text-dim">A count corrects stock; a build makes an item from its parts.</p>
        <div className="flex gap-2">
          <button className={btn} disabled={busy} onClick={() => start('count')}>Count / adjust stock</button>
          <button className={btn} disabled={busy} onClick={() => start('production')}>Build an item</button>
        </div>
      </div>
    );
  }
  if (!wo) return <div className="p-4 db-text-dim">Loading…</div>;

  const editable = !complete && !(kind === 'production' && fullBom);
  const empty = lines.length === 0 && rows.length === 0 && !complete;
  return (
    <div className="p-3 space-y-3" style={{ fontSize: 13 }}>
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="text-base font-semibold">Workorder {wo.ida || wo.id}</h2>
        <span className="rounded px-2 py-0.5 text-xs" style={{ border: '1px solid var(--db-border)' }}>
          {kind === 'count' ? 'Count / adjust' : 'Build'}
        </span>
        <span className="text-xs db-text-dim">{complete ? 'Complete' : wo.status || 'open'}</span>
        {empty && (
          <span className="flex gap-1 text-xs">
            <button className={btn} disabled={busy || kind === 'count'} onClick={() => choose('count')}>Make it a count</button>
            <button className={btn} disabled={busy || kind === 'production'} onClick={() => choose('production')}>Make it a build</button>
          </span>
        )}
        {kind === 'production' && fullBom && !complete && (
          <span className="text-xs" title="Its lines follow the BOM. Change the BOM and expand again, or expand one level to edit lines by hand.">
            Expanded from the full BOM: lines are locked
          </span>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr className="db-text-dim text-xs">
            <th style={cell}></th><th style={{ ...cell, textAlign: 'left' }}>Item</th>
            {kind === 'count'
              ? (<><th style={num}>Book</th><th style={num}>Counted / change</th><th style={num}>Variance</th><th style={{ ...cell, textAlign: 'left' }}>Reason</th></>)
              : (<><th style={num}>Qty</th><th style={num}>Unit cost</th><th style={num}>Cost</th><th style={{ ...cell, textAlign: 'left' }}></th></>)}
            <th style={cell}></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => {
            const ev = lastEvent(l);
            const active = Number(l.quantity?.active || 0);
            return (
              <tr key={l.id}>
                <td style={cell} title={l.line_type}>{SIGN[l.line_type] || ''} {l.line_type}</td>
                <td style={{ ...cell, paddingLeft: 6 + 14 * depthOf(l) }}>{itemLabel(l)}</td>
                {kind === 'count' ? (
                  <>
                    <td style={num}>{l.line_type === 'count' ? l.quantity?.staged ?? '' : ''}</td>
                    <td style={num}>
                      {l.line_type === 'count' && !complete ? (
                        <input type="number" className="w-20 text-right" value={recount[l.id] ?? String(active)}
                               onChange={(e) => setRecount((p) => ({ ...p, [l.id]: e.target.value }))} />
                      ) : active}
                    </td>
                    <td style={num}>{l.line_type === 'count' ? active - Number(l.quantity?.staged || 0) : active}</td>
                    <td style={cell}>{lastReason(l)}{ev?.moved_during_count ? ' (stock moved during the count)' : ''}</td>
                  </>
                ) : (
                  <>
                    <td style={num}>{active}</td>
                    {(() => {
                      // A build line shows what it was made at; a − line what it took per unit.
                      // (In the record a layer put on the shelf is negative; here it reads as value.)
                      const total = ev ? Math.abs(Number(ev.consumed?.cost ?? ev.parts_cost ?? ev.cost ?? 0)) : undefined;
                      const unit = l.line_type === 'build'
                        ? (ev?.unit_cost ?? l.cost?.unit)
                        : (total !== undefined && active ? total / Math.abs(active) : l.cost?.unit);
                      return (<><td style={num}>{money(unit)}</td><td style={num}>{money(total)}</td></>);
                    })()}
                    <td style={cell}>
                      {l.line_type === 'build' && !l.refs?.bom?.parent_line_id && !complete && (
                        <span className="flex gap-1">
                          <button className={btn} disabled={busy} onClick={() => expand(l, 1)}>Expand one level</button>
                          <button className={btn} disabled={busy} onClick={() => expand(l, 0)}>Full BOM</button>
                        </span>
                      )}
                    </td>
                  </>
                )}
                <td style={cell}>
                  {editable && !(l.events || []).length && (
                    <button className={btn} disabled={busy} onClick={() => remove(l)} title="Remove this line">×</button>
                  )}
                </td>
              </tr>
            );
          })}

          {rows.map((r) => (
            <tr key={r.key}>
              <td style={cell}>
                <select value={r.line_type} onChange={(e) => setRow(r.key, { line_type: e.target.value as LineType })}>
                  {(kind === 'count' ? ['count', 'adjust'] : ['build', 'consume', 'scrap']).map((t) => (
                    <option key={t} value={t}>{SIGN[t as LineType]} {t}</option>
                  ))}
                </select>
              </td>
              <td style={cell}>{r.label}</td>
              {kind === 'count' ? (
                <>
                  <td style={num}>{r.line_type === 'count' ? r.on_hand : ''}</td>
                  <td style={num}><input type="number" className="w-20 text-right" value={r.qty} autoFocus
                                         onChange={(e) => setRow(r.key, { qty: e.target.value })} /></td>
                  <td style={num}>{r.line_type === 'count' ? Number(r.qty || 0) - r.on_hand : Number(r.qty || 0)}</td>
                  <td style={cell}>
                    <input list="wo-reasons" className="w-full" placeholder={r.line_type === 'adjust' ? 'reason (required)' : 'note'}
                           value={r.reason} onChange={(e) => setRow(r.key, { reason: e.target.value })} />
                  </td>
                </>
              ) : (
                <>
                  <td style={num}><input type="number" className="w-20 text-right" value={r.qty} autoFocus
                                         onChange={(e) => setRow(r.key, { qty: e.target.value })} /></td>
                  <td style={num}><input type="number" className="w-20 text-right" value={r.unit_cost}
                                         placeholder={r.line_type === 'build' ? 'if no BOM' : ''}
                                         onChange={(e) => setRow(r.key, { unit_cost: e.target.value })} /></td>
                  <td style={cell}></td><td style={cell}></td>
                </>
              )}
              <td style={cell}><button className={btn} onClick={() => setRows((p) => p.filter((x) => x.key !== r.key))}>×</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <datalist id="wo-reasons">{REASONS.map((r) => <option key={r} value={r} />)}</datalist>

      {editable && (
        <div className="relative" style={{ maxWidth: 420 }}>
          <input className="w-full" placeholder="Add an item: search or scan, Enter adds the first match"
                 value={search} onChange={(e) => find(e.target.value)}
                 onKeyDown={(e) => { if (e.key === 'Enter' && found[0]) add(found[0]); }} />
          {found.length > 0 && (
            <div className="absolute z-10 w-full rounded shadow" style={{ background: 'var(--db-bg, #fff)', border: '1px solid var(--db-border)' }}>
              {found.map((it) => (
                <div key={it.id} className="px-2 py-1 cursor-pointer hover:bg-gray-100" onClick={() => add(it)}>
                  {[it.ida, it.name].filter(Boolean).join(' — ')}
                  <span className="db-text-dim"> · on hand {Number(it.quantity?.on_hand || 0)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        {(rows.length > 0 || Object.keys(recount).length > 0) && (
          <button className={btn} disabled={busy} onClick={save}>
            {kind === 'count' ? 'Save (moves stock)' : 'Save lines'}
          </button>
        )}
        {kind === 'production' && !complete && lines.some((l) => l.line_type === 'build') && rows.length === 0 && (
          <button className={btn} disabled={busy} onClick={finish}>Complete build</button>
        )}
      </div>
      {kind === 'production' && !complete && (
        <p className="text-xs db-text-dim">
          One workorder per build: Complete makes the whole quantity and closes the workorder.
        </p>
      )}
    </div>
  );
}
