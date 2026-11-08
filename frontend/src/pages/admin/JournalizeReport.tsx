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
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { manageAction } from '@/api/wcapi';
import RecordLink from '@/components/common/RecordLink';
import { formatCurrency } from '@/utils/stringUtils';
import { formatDt } from '@/utils/fieldFormatters';

export const POSTING_MODELS = ['invoice', 'cash', 'receipt', 'workorder'] as const;
export type PostingModel = typeof POSTING_MODELS[number];

interface Entry { account: string; name: string; debit: number; credit: number; purpose: string }
interface Preview { posted: boolean; entries: Entry[]; debits: number; credits: number; balanced: boolean; note: string }
export interface ReportRow {
  id: number; ida: string; status: string; party: string; total: number | null; dt_created: number;
  waiting: string; preview: Preview | null;
  /** What posting this ready row also does — releases a planned invoice (Bill, 2026-11-08). */
  note?: string;
}
interface Report { model: string; rows: ReportRow[]; ready: number; waiting: number; total: number; limit: number }
interface RowAnswer { id: number; ida: string; created?: number; code?: string; message?: string; messages?: string[] }
interface RunAnswer { model: string; posted: RowAnswer[]; refused: RowAnswer[]; batch: string }

/** The ids a Post may send: the ticked rows that are ready. */
export function postable(rows: ReportRow[], ticked: Set<number>): number[] {
  return rows.filter((r) => !r.waiting && ticked.has(r.id)).map((r) => r.id);
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

  const load = useCallback(async () => {
    if (!known) return;
    setError('');
    try {
      const res = await manageAction('execute_report', { report_key: `journalize_${model}`, report_params: {} });
      setReport(res?.result as Report);
      setTicked(new Set());
    } catch (e: any) { setError(e?.response?.data?.message || e?.message || 'The report did not load'); }
  }, [model, known]);
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
  const flip = (id: number) => setOpen((o) => flipIn(o, id));

  const post = async () => {
    if (!ids.length) return;
    if (!confirm(`Post ${ids.length} ${model}${ids.length === 1 ? '' : 's'} to the GL? Each posted record locks.`)) return;
    setPosting(true);
    setError('');
    try {
      const res = await manageAction('journalize_selected', { model, ids });
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
          {report ? `${report.total} unposted · ${report.ready} ready · ${report.waiting} waiting${report.total > report.limit ? ` · showing the oldest ${report.limit}` : ''}` : 'Loading…'}
        </span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="fs-btn" onClick={() => setTicked(new Set(readyIds))} disabled={!readyIds.length}>Tick all ready</button>
          <button className="fs-btn" onClick={() => setTicked(new Set())} disabled={!ticked.size}>Clear</button>
          <button className="fs-btn" onClick={post} disabled={posting || !ids.length}
                  title="Each ticked row posts through its own journalize command; a refusal on one stops nothing else">
            {posting ? 'Posting…' : `Post ${ids.length || ''}`.trim()}
          </button>
          <button className="fs-btn" onClick={load} disabled={posting}>Reload</button>
        </span>
      </div>
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
