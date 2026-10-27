/**
 * JournalEntriesPanel — the journal entry each document makes, in the flight simulator
 * (Bill, 2026-10-27: "a teaching tool rather than an accounting tool").
 *
 * For the simulation's invoices, cash and receipts: the entry the server WILL post (preview —
 * the real journalize, rolled back), then Post to journalize it for real, and the entry moves
 * to Posted. "Explain" switches between plain words and the ledger table; the same entries
 * either way. POST /wcapi/<model>/<id>/journal_preview/ and …/journalize/.
 */
import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '@/api/axios';
import { formatCurrency } from '@/utils/stringUtils';

export interface JournalDoc { model: 'invoice' | 'cash' | 'receipt'; id: number; ida: string }

interface Entry { account: string; name: string; debit: number; credit: number; purpose: string }
interface Preview { posted: boolean; entries: Entry[]; debits: number; credits: number; balanced: boolean; note: string }

const EXPLAIN_KEY = 'flightsim.journal.explain';

/** What a line means, said plainly — by the account's role (the code after its number:
 *  1100-accounts_receivable), then by side. The GL rows carry no purpose, so the role is the
 *  reliable key. */
const MEANING: Record<string, { debit?: string; credit?: string }> = {
  accounts_receivable: { debit: 'the customer owes us more', credit: 'the customer owes us less' },
  sales_revenue: { credit: 'we earned revenue from the sale', debit: 'revenue taken back' },
  sales_discounts: { debit: 'a discount we gave reduces what we earned' },
  cost_of_goods_sold: { debit: 'what the goods cost us becomes an expense of the sale' },
  inventory: { debit: 'goods arrived on our shelves', credit: 'goods left our shelves' },
  sales_tax_payable: { credit: 'tax we collected and now owe the state', debit: 'tax we paid the state' },
  shipping_revenue: { credit: 'shipping we charged the customer' },
  cash: { debit: 'money arrived in the bank', credit: 'money left the bank' },
  undeposited_funds: { debit: 'money received, not yet deposited', credit: 'money deposited' },
  bad_debt: { debit: 'what we will not collect becomes a loss' },
  small_balance_writeoff: { debit: 'a small balance we will not collect becomes a loss' },
  accounts_payable: { credit: 'we owe the vendor', debit: 'we owe the vendor less' },
  received_not_billed: { debit: 'goods received, waiting for the vendor\'s bill',
                         credit: 'goods received, waiting for the vendor\'s bill' },
  opening_balance_equity: { credit: 'what the business started with', debit: 'what the business started with' },
};

const role = (account: string) => account.replace(/^[0-9]+-/, '');

function meaning(e: Entry): string {
  const side = e.debit ? 'debit' : 'credit';
  return MEANING[role(e.account)]?.[side] ?? `${side} ${e.name}`;
}

function headline(doc: JournalDoc, p: Preview): string {
  if (!p.entries.length) return `${doc.model === 'cash' ? 'Cash' : doc.model === 'invoice' ? 'Invoice' : 'Receipt'} ${doc.ida}`;
  const sum = (r: string, side: 'debit' | 'credit') =>
    p.entries.filter((e) => role(e.account) === r).reduce((t, e) => t + e[side], 0);
  if (doc.model === 'invoice') {
    return `Invoice ${doc.ida}: we sold goods — the customer owes us ${formatCurrency(sum('accounts_receivable', 'debit'))}`;
  }
  if (doc.model === 'receipt') {
    return `Receipt ${doc.ida}: goods arrived — we owe the vendor ${formatCurrency(sum('accounts_payable', 'credit'))}`;
  }
  const lost = sum('bad_debt', 'debit') + sum('small_balance_writeoff', 'debit');
  if (lost) return `Cash ${doc.ida}: we write off ${formatCurrency(lost)} the customer will not pay`;
  const out = sum('cash', 'credit');
  if (out) return `Cash ${doc.ida}: we paid out ${formatCurrency(out)}`;
  return `Cash ${doc.ida}: the customer paid us ${formatCurrency(sum('cash', 'debit') + sum('undeposited_funds', 'debit'))}`;
}

async function command(doc: JournalDoc, verb: 'journal_preview' | 'journalize') {
  const res = await apiClient.post(`/wcapi/${doc.model}/${doc.id}/${verb}/`, {});
  return res.data?.data?.result;
}

const DocEntry: React.FC<{ doc: JournalDoc; explain: boolean; onPosted: () => void }> = ({ doc, explain, onPosted }) => {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState('');
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try { setPreview(await command(doc, 'journal_preview')); }
    catch (e: any) { setError(e?.response?.data?.message || e?.message || 'Preview failed'); }
  }, [doc]);
  useEffect(() => { load(); }, [load]);

  const post = async () => {
    setPosting(true);
    setError('');
    try { await command(doc, 'journalize'); await load(); onPosted(); }
    catch (e: any) { setError(e?.response?.data?.message || e?.message || 'Post failed'); }
    finally { setPosting(false); }
  };

  return (
    <div className="fs-journal-doc" style={{ borderBottom: '1px solid var(--db-border-light, #e9ecef)', padding: '6px 8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <strong style={{ fontSize: 12 }}>{preview ? headline(doc, preview) : `${doc.model} ${doc.ida}`}</strong>
        {preview && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8,
                         background: preview.posted ? 'var(--db-bg-row-active, #e7f1ff)' : 'var(--db-surface-alt, #f1f3f5)' }}>
            {preview.posted ? 'Posted' : 'Preview'}
          </span>
        )}
        {preview && !preview.posted && preview.entries.length > 0 && (
          <button className="fs-btn" style={{ marginLeft: 'auto' }} onClick={post} disabled={posting}
                  title="Journalize this document: the entry below is written to the GL and the document locks">
            {posting ? 'Posting…' : 'Post'}
          </button>
        )}
      </div>
      {error && <div style={{ color: 'var(--db-accent-red, #c92a2a)', fontSize: 11 }}>{error}</div>}
      {preview && !preview.entries.length && <div style={{ fontSize: 11, opacity: 0.7 }}>{preview.note}</div>}
      {preview && preview.entries.length > 0 && (explain ? (
        <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11, marginTop: 4 }}>
          {[...preview.entries].sort((a, b) => (b.debit ? 1 : 0) - (a.debit ? 1 : 0)).map((e, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '2.2em 16em 7em 1fr', paddingLeft: e.debit ? 0 : '1.5em' }}>
              <span>{e.debit ? 'Dr' : 'Cr'}</span>
              <span title={e.account}>{e.name}</span>
              <span style={{ textAlign: 'right' }}>{formatCurrency(e.debit || e.credit)}</span>
              <span style={{ opacity: 0.7, paddingLeft: 8 }}>— {meaning(e)}</span>
            </div>
          ))}
          <div style={{ marginTop: 2, opacity: 0.8 }}>
            Debits {formatCurrency(preview.debits)} {preview.balanced ? '=' : '≠'} Credits {formatCurrency(preview.credits)} {preview.balanced ? '✓' : '✗'}
          </div>
        </div>
      ) : (
        <table style={{ width: '100%', fontSize: 11, marginTop: 4 }}>
          <thead><tr style={{ opacity: 0.7, textAlign: 'left' }}>
            <th>Account</th><th>Name</th><th style={{ textAlign: 'right' }}>Debit</th><th style={{ textAlign: 'right' }}>Credit</th>
          </tr></thead>
          <tbody>
            {preview.entries.map((e, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'ui-monospace, monospace' }}>{e.account}</td>
                <td>{e.name}</td>
                <td style={{ textAlign: 'right' }}>{e.debit ? formatCurrency(e.debit) : ''}</td>
                <td style={{ textAlign: 'right' }}>{e.credit ? formatCurrency(e.credit) : ''}</td>
              </tr>
            ))}
            <tr style={{ borderTop: '1px solid var(--db-border-light, #e9ecef)', fontWeight: 600 }}>
              <td colSpan={2}>{preview.balanced ? 'Balanced' : 'OUT OF BALANCE'}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(preview.debits)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(preview.credits)}</td>
            </tr>
          </tbody>
        </table>
      ))}
    </div>
  );
};

const JournalEntriesPanel: React.FC<{ docs: JournalDoc[]; onPosted: () => void }> = ({ docs, onPosted }) => {
  const [explain, setExplain] = useState<boolean>(() => {
    try { return localStorage.getItem(EXPLAIN_KEY) !== 'table'; } catch { return true; }
  });
  const toggle = (on: boolean) => {
    setExplain(on);
    try { localStorage.setItem(EXPLAIN_KEY, on ? 'explain' : 'table'); } catch { /* per-viewer convenience only */ }
  };
  return (
    <>
      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, padding: '4px 8px' }}>
        <input type="checkbox" checked={explain} onChange={(e) => toggle(e.target.checked)} />
        Explain — plain words instead of the ledger table
      </label>
      {docs.length ? docs.map((d) => (
        <DocEntry key={`${d.model}:${d.id}`} doc={d} explain={explain} onPosted={onPosted} />
      )) : <div className="fs-section-empty">No invoice, cash or receipt yet</div>}
    </>
  );
};

export default JournalEntriesPanel;
