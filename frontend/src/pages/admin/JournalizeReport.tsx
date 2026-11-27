/**
 * JournalizeReport — one model's unposted records, ready or waiting (Bill, 2026-11-07: "There
 * should be a user report to journalize documents. It should not be automatic." "We should have
 * a report for every model that displays unjournalized records. The users then choose the
 * records they want journalized and post them.")
 *
 * /journalize/:model for invoice, cash, receipt, workorder. The list comes from the report's
 * executor (manage execute_report, report_key journalize_<model>): each row ready, with the entry
 * it will post (the real posting, rolled back), or waiting, with the reason in the door's or the
 * poster's words and no tick box. Post sends the ticked ids to journalize_selected: every row goes
 * through the door command on its own, and the answer comes back per row.
 *
 * 2026-11-27 (Bill: journalize at least weekly): a period (begin/end, local dates, by dt_created)
 * chooses the rows; it does not date the GL. A receipt with charges no line carries shows them and
 * its own "post unallocated" tick, never ticked by default, sent for that row only. A row that
 * posts no GL entry (a zero cash, a workorder whose work carried no value) is ready and noted.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { manageAction } from '@/api/wcapi';
import RecordLink from '@/components/common/RecordLink';
import { formatCurrency } from '@/utils/stringUtils';
import { formatDt } from '@/utils/fieldFormatters';
import SendPeriodToAccounting from './SendPeriodToAccounting';

export const POSTING_MODELS = ['invoice', 'cash', 'receipt', 'workorder'] as const;
export type PostingModel = typeof POSTING_MODELS[number];

interface Entry { account: string; name: string; debit: number; credit: number; purpose: string }
interface Preview { posted: boolean; entries: Entry[]; debits: number; credits: number; balanced: boolean; note: string }
export interface ReportRow {
  id: number; ida: string; status: string; party: string; total: number | null; dt_created: number;
  waiting: string; preview: Preview | null;
  /** What posting this ready row also does — releases a planned invoice (Bill, 2026-11-08). */
  note?: string;
  /** A receipt's charges no line carries, by kind: posted only with this row's own tick. */
  unallocated?: Record<string, number>;
}
interface Report {
  model: string; rows: ReportRow[]; ready: number; waiting: number; total: number; limit: number;
  begin?: number | null; end?: number | null;
}
interface RowAnswer { id: number; ida: string; created?: number; code?: string; message?: string; messages?: string[] }
interface RunAnswer { model: string; posted: RowAnswer[]; refused: RowAnswer[]; batch: string }

/** The ids a Post may send: the ticked rows that are ready. */
export function postable(rows: ReportRow[], ticked: Set<number>): number[] {
  return rows.filter((r) => !r.waiting && ticked.has(r.id)).map((r) => r.id);
}

/** Each posted row's own choices: post_unallocated only for a row the person ticked for it. */
export function rowOptions(rows: ReportRow[], ids: number[], unallocTicked: Set<number>):
    Record<string, { post_unallocated: true }> {
  const sending = new Set(ids);
  return Object.fromEntries(rows
    .filter((r) => sending.has(r.id) && r.unallocated && unallocTicked.has(r.id))
    .map((r) => [String(r.id), { post_unallocated: true as const }]));
}

/** The period as the report takes it: a local date's first and last moment, as UTC epoch ms. */
export function periodParams(begin: string, end: string): { begin?: number; end?: number } {
  const at = (day: string, h: number, m: number, sec: number, ms: number) => {
    const [y, mo, d] = day.split('-').map(Number);
    return new Date(y, mo - 1, d, h, m, sec, ms).getTime();
  };
  return { ...(begin ? { begin: at(begin, 0, 0, 0, 0) } : {}), ...(end ? { end: at(end, 23, 59, 59, 999) } : {}) };
}

const th: React.CSSProperties = { textAlign: 'left', padding: '4px 6px', borderBottom: '1px solid var(--db-border, #d1d5db)', fontSize: 11, whiteSpace: 'nowrap' };
const td: React.CSSProperties = { padding: '3px 6px', borderBottom: '1px solid var(--db-border-light, #e9ecef)', fontSize: 12, verticalAlign: 'top' };

const EntryLines: React.FC<{ preview: Preview }> = ({ preview }) => (
  <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11, padding: '2px 0 4px 0' }}>
    {[...preview.entries].sort((a, b) => (b.debit ? 1 : 0) - (a.debit ? 1 : 0)).map((e, i) => (
      <div key={i} style={{ display: 'grid', gridTemplateColumns: '2.2em 18em 8em', paddingLeft: e.debit ? 0 : '1.5em' }}>
        <span>{e.debit ? 'Dr' : 'Cr'}</span>
        <span title={e.account}>{e.name}</span>
        <span style={{ textAlign: 'right' }}>{formatCurrency(e.debit || e.credit)}</span>
      </div>
    ))}
    <div style={{ opacity: 0.8, marginTop: 2 }}>
      Debits {formatCurrency(preview.debits)} {preview.balanced ? '=' : '≠'} Credits {formatCurrency(preview.credits)} {preview.balanced ? '✓' : '✗'}
    </div>
  </div>
);

const JournalizeReport: React.FC = () => {
  const { model = '' } = useParams<{ model: string }>();
  const known = (POSTING_MODELS as readonly string[]).includes(model);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const [ticked, setTicked] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState<Set<number>>(new Set());
  const [posting, setPosting] = useState(false);
  const [answer, setAnswer] = useState<RunAnswer | null>(null);
  const [unallocTicked, setUnallocTicked] = useState<Set<number>>(new Set());
  const [begin, setBegin] = useState('');
  const [end, setEnd] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    if (!known) return;
    setError('');
    try {
      const res = await manageAction('execute_report', { report_key: `journalize_${model}`,
                                                         report_params: periodParams(begin, end) });
      setReport(res?.result as Report);
      setTicked(new Set());
      setUnallocTicked(new Set());
    } catch (e: any) { setError(e?.response?.data?.message || e?.message || 'The report did not load'); }
  }, [model, known, begin, end]);
  useEffect(() => { load(); }, [load]);

  const rows = report?.rows ?? [];
  const ids = useMemo(() => postable(rows, ticked), [rows, ticked]);
  const readyIds = useMemo(() => rows.filter((r) => !r.waiting).map((r) => r.id), [rows]);
  const answers = useMemo(() => {
    const m = new Map<number, RowAnswer & { ok: boolean }>();
    answer?.posted.forEach((a) => m.set(a.id, { ...a, ok: true }));
    answer?.refused.forEach((a) => m.set(a.id, { ...a, ok: false }));
    return m;
  }, [answer]);

  const flipIn = (set: Set<number>, id: number) => { const n = new Set(set); if (n.has(id)) n.delete(id); else n.add(id); return n; };
  const toggle = (id: number) => setTicked((t) => flipIn(t, id));
  const toggleUnalloc = (id: number) => setUnallocTicked((t) => flipIn(t, id));
  const flip = (id: number) => setOpen((o) => flipIn(o, id));

  const post = async () => {
    if (!ids.length) return;
    if (!confirm(`Post ${ids.length} ${model}${ids.length === 1 ? '' : 's'} to the GL? Each posted record locks.`)) return;
    setPosting(true);
    setError('');
    try {
      const res = await manageAction('journalize_selected', { model, ids, options: rowOptions(rows, ids, unallocTicked) });
      setAnswer(res as RunAnswer);
      await load();
    } catch (e: any) { setError(e?.response?.data?.message || e?.message || 'The run failed'); }
    finally { setPosting(false); }
  };

  if (!known) {
    return <div style={{ padding: 16 }}>No journalize report for “{model}”. There is one for {POSTING_MODELS.join(', ')}.</div>;
  }

  return (
    <div style={{ padding: '8px 12px', color: 'var(--db-text, #212529)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <h2 style={{ fontSize: 15, margin: 0 }}>Journalize {model}s</h2>
        <span style={{ fontSize: 11, opacity: 0.75 }}>
          {report ? `${report.total} unposted${begin || end ? ` from ${begin || 'the start'} to ${end || 'today'}` : ''} · ${report.ready} ready · ${report.waiting} waiting${report.total > report.limit ? ` · showing the oldest ${report.limit}` : ''}` : 'Loading…'}
        </span>
        <label style={{ fontSize: 11 }} title="Created on or after this day (your local date)">From{' '}
          <input type="date" value={begin} onChange={(e) => setBegin(e.target.value)} data-wc="journalize-begin" /></label>
        <label style={{ fontSize: 11 }} title="Created on or before this day (your local date)">to{' '}
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} data-wc="journalize-end" /></label>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="fs-btn" onClick={() => setTicked(new Set(readyIds))} disabled={!readyIds.length}>Tick all ready</button>
          <button className="fs-btn" onClick={() => setTicked(new Set())} disabled={!ticked.size}>Clear</button>
          <button className="fs-btn" onClick={post} disabled={posting || !ids.length}
                  title="Each ticked row posts through its own journalize command; a refusal on one stops nothing else">
            {posting ? 'Posting…' : `Post ${ids.length || ''}`.trim()}
          </button>
          <button className="fs-btn" onClick={load} disabled={posting}>Reload</button>
          <button className="fs-btn" onClick={() => setSending((v) => !v)} aria-expanded={sending}
                  title="The month's posted GL, by its documents' period, as a file for the accountant">
            Send period to accounting
          </button>
        </span>
      </div>
      {sending && <SendPeriodToAccounting />}
      {error && <div style={{ color: 'var(--db-accent-red, #c92a2a)', fontSize: 12, marginBottom: 6 }}>{error}</div>}
      {answer && (
        <div style={{ fontSize: 12, marginBottom: 6, padding: '4px 8px', background: 'var(--db-surface-alt, #f1f3f5)', borderRadius: 4 }}>
          Run {answer.batch}: {answer.posted.length} posted, {answer.refused.length} refused.
          {answer.refused.map((r) => <div key={r.id} style={{ color: 'var(--db-accent-red, #c92a2a)' }}>{r.ida || r.id}: {r.message}</div>)}
        </div>
      )}
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={th}></th>
            <th style={th}>Record</th>
            <th style={th}>Status</th>
            <th style={th}>Party</th>
            <th style={{ ...th, textAlign: 'right' }}>Total</th>
            <th style={th}>Created</th>
            <th style={th}>Ready / waiting because</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const a = answers.get(r.id);
            return (
              <React.Fragment key={r.id}>
                <tr>
                  <td style={td}>
                    {r.waiting ? <span title="Not ready: see why" style={{ opacity: 0.4 }}>—</span>
                      : <input type="checkbox" checked={ticked.has(r.id)} onChange={() => toggle(r.id)} />}
                  </td>
                  <td style={td}><RecordLink model={model} id={r.id} label={r.ida || String(r.id)} /></td>
                  <td style={td}>{r.status}</td>
                  <td style={td}>{r.party}</td>
                  <td style={{ ...td, textAlign: 'right' }}>{r.total == null ? '' : formatCurrency(r.total)}</td>
                  <td style={td}>{formatDt(r.dt_created, 'date', 'dt_created')}</td>
                  <td style={td}>
                    {r.waiting ? <span style={{ opacity: 0.85 }}>{r.waiting}</span> : (
                      <button className="fs-btn" onClick={() => flip(r.id)} title="The entry this record will post">
                        {open.has(r.id) ? 'Hide entry' : `Ready — ${r.preview?.entries.length ?? 0} lines`}
                      </button>
                    )}
                    {!r.waiting && r.note && <div style={{ fontSize: 11, opacity: 0.8 }} data-wc="journalize-note">{r.note}</div>}
                    {!r.waiting && r.unallocated && (
                      <label style={{ display: 'block', fontSize: 11 }} data-wc="journalize-unallocated"
                             title="Charges no line carries post to the unallocated-receipt account, not to inventory">
                        <input type="checkbox" checked={unallocTicked.has(r.id)} onChange={() => toggleUnalloc(r.id)} />{' '}
                        Post unallocated: {Object.entries(r.unallocated).map(([k, v]) => `${k} ${formatCurrency(v)}`).join(', ')}
                      </label>
                    )}
                    {a && <div style={{ fontSize: 11, color: a.ok ? 'var(--db-accent-green, #2b8a3e)' : 'var(--db-accent-red, #c92a2a)' }}>
                      {a.ok ? [`Posted ${a.created} lines`, ...(a.messages || [])].join('. ') : a.message}</div>}
                  </td>
                </tr>
                {open.has(r.id) && r.preview && (
                  <tr><td style={td} /><td style={td} colSpan={6}><EntryLines preview={r.preview} /></td></tr>
                )}
              </React.Fragment>
            );
          })}
          {report && !rows.length && <tr><td style={td} colSpan={7}>Every {model} is posted.</td></tr>}
        </tbody>
      </table>
    </div>
  );
};

export default JournalizeReport;
