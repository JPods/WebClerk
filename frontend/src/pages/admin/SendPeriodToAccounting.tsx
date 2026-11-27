/**
 * SendPeriodToAccounting — the month's GL, as a file for the accountant (2026-11-27).
 *
 * Bill: users journalize at least weekly; then the period goes to accounting. Choose a month, see
 * what it holds — rows, debits, credits, balanced — and download it in the accountant's format.
 * Everything comes from GET /wcapi/reports/gl-export/ (build_gl_journal_bundle): a row belongs to
 * its document's period (dt_document), not the day it posted. The month is a UTC month. The
 * figures shown are the server's (the bundle's totals), never a sum made here. Accounting, admin
 * and superuser only (access.ACCOUNTING_ROLES); anyone else is told so by the server.
 */
import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '@/api/axios';
import { formatCurrency } from '@/utils/stringUtils';

const URL = '/wcapi/reports/gl-export/';
/** The format whose answer carries the bundle's totals; the check reads them from it. */
export const CHECK_FORMAT = 'GL Export — Generic JSON';

export interface PeriodTotals { entry_count: number; total_debits: number; total_credits: number; balanced: boolean }

/** This month, as the endpoint takes it: YYYY-MM. */
export function thisMonth(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

/** The file name the server gave (Content-Disposition), else one made from the period. */
export function fileNameOf(disposition: string | undefined, period: string): string {
  const named = /filename="?([^";]+)"?/i.exec(disposition || '');
  return named ? named[1] : `${period}_gl_journal`;
}

const errorOf = (e: any, fallback: string) =>
  e?.response?.data?.message || e?.response?.data?.detail || e?.message || fallback;

const SendPeriodToAccounting: React.FC = () => {
  const [period, setPeriod] = useState(thisMonth());
  const [formats, setFormats] = useState<string[]>([]);
  const [format, setFormat] = useState('');
  const [totals, setTotals] = useState<PeriodTotals | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  // The formats are the server's list (gl_export.REPORT_NAME_MAP): asked, not copied here.
  useEffect(() => {
    apiClient.get(URL).catch((e: any) => {
      const available: string[] = e?.response?.data?.error?.available || [];
      setFormats(available);
      setFormat((f) => f || available[0] || '');
      if (!available.length) setError(errorOf(e, 'The export formats did not load'));
    });
  }, []);

  const check = useCallback(async () => {
    setBusy(true); setError(''); setTotals(null);
    try {
      const res = await apiClient.get(URL, { params: { report: CHECK_FORMAT, period } });
      const bundle = res.data?.data ?? res.data;          // the JSON answer comes in the API envelope
      setTotals(bundle?.totals ?? null);
    } catch (e: any) { setError(errorOf(e, 'The period did not load')); }
    finally { setBusy(false); }
  }, [period]);

  const download = useCallback(async () => {
    if (!format) return;
    setBusy(true); setError('');
    try {
      const res = await apiClient.get(URL, { params: { report: format, period }, responseType: 'blob' });
      const a = document.createElement('a');
      a.href = URL_.createObjectURL(res.data as Blob);
      a.download = fileNameOf(res.headers?.['content-disposition'], period);
      a.click();
      URL_.revokeObjectURL(a.href);
    } catch (e: any) { setError(errorOf(e, 'The download failed')); }
    finally { setBusy(false); }
  }, [format, period]);

  return (
    <div data-wc="send-period" style={{ fontSize: 12, padding: '6px 8px', marginBottom: 8,
         background: 'var(--db-surface-alt, #f1f3f5)', borderRadius: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <strong>Send period to accounting</strong>
        <label title="The month's GL rows by their document's date (dt_document), a UTC month">Month{' '}
          <input type="month" value={period} onChange={(e) => { setPeriod(e.target.value); setTotals(null); }} />
        </label>
        <button className="fs-btn" onClick={check} disabled={busy || !period}>Check</button>
        <label>Format{' '}
          <select value={format} onChange={(e) => setFormat(e.target.value)} disabled={!formats.length}>
            {formats.map((f) => <option key={f} value={f}>{f.replace('GL Export — ', '')}</option>)}
          </select>
        </label>
        <button className="fs-btn" onClick={download} disabled={busy || !period || !format}>Download</button>
      </div>
      {totals && (
        <div style={{ marginTop: 4 }} data-wc="send-period-totals">
          {period}: {totals.entry_count} rows · Debits {formatCurrency(totals.total_debits)}{' '}
          {totals.balanced ? '=' : '≠'} Credits {formatCurrency(totals.total_credits)} {totals.balanced ? '✓' : '✗'}
        </div>
      )}
      {error && <div style={{ marginTop: 4, color: 'var(--db-accent-red, #c92a2a)' }}>{error}</div>}
    </div>
  );
};

const URL_ = window.URL;

export default SendPeriodToAccounting;
