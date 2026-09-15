/**
 * CommissionReportPrintDocument — commission reports for reps and sales.
 *
 * Two modes:
 *   1. Company summary — all reps, one line per rep, period totals
 *   2. Individual rep statement — one rep, invoice-level detail
 *
 * Staff-only (gated by reportLists role_required + backend staff check).
 */
import React from 'react';
import { formatCurrency } from './printTypes';
import { formatPercent } from '@/utils/stringUtils';
import { formatDt } from '@/utils/fieldFormatters';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CommissionReportRepLine {
  rep_id: number;
  rep_ida: string;
  name: string;
  basis: string;
  rate_pct: number;
  sales_credited: number;
  commission_earned: number;
  invoice_count: number;
  accrued: number;
  paid: number;
  pending: number;
}

export interface CommissionDetailLine {
  invoice_id: number;
  invoice_ida: string;
  date: string;
  customer: string;
  sale_amount: number;
  credited: number;
  rate_pct: number;
  effective_rate: number;
  commission: number;
  accrued: boolean;
}

export interface CommissionReportData {
  period_label: string;
  period_start: string;
  period_end: string;
  company: {
    name: string;
    address: string;
    city_state_zip: string;
    phone: string;
    logo_url?: string;
  };
  reps: (CommissionReportRepLine & { detail?: CommissionDetailLine[] })[];
  total_sales: number;
  total_commission: number;
  total_invoices: number;
  /** When set, this is a single-rep detail report */
  rep_name?: string;
}

const fmt = (n: number) => formatCurrency(n);

// ---------------------------------------------------------------------------
// Company Summary
// ---------------------------------------------------------------------------

function CompanySummary({ data }: { data: CommissionReportData }) {
  const { company, reps, period_label, total_sales, total_commission, total_invoices } = data;

  return (
    <div className="print-page">
      <Header company={company} title="Commission Report" periodLabel={period_label} data={data} />

      <table className="print-table-lg">
        <thead>
          <tr className="print-thead-row">
            <th className="print-th">representative</th>
            <th className="print-th-c">basis</th>
            <th className="print-th-r">rate</th>
            <th className="print-th-r">invoices</th>
            <th className="print-th-r">sales credited</th>
            <th className="print-th-r">commission</th>
            <th className="print-th-r">accrued</th>
            <th className="print-th-r">paid</th>
            <th className="print-th-r">pending</th>
          </tr>
        </thead>
        <tbody>
          {reps.map((rep, i) => (
            <tr key={i} className="print-row">
              <td className="print-td">
                <div className="print-semibold">{rep.name}</div>
                <div className="print-text-xs print-text-dim">{rep.rep_ida}</div>
              </td>
              <td className="print-td print-center print-text-sm">{rep.basis}</td>
              <td className="print-td-r">{formatPercent(rep.rate_pct)}</td>
              <td className="print-td-r">{rep.invoice_count}</td>
              <td className="print-td-mono">{fmt(rep.sales_credited)}</td>
              <td className="print-td-bold-mono">{fmt(rep.commission_earned)}</td>
              <td className="print-td-mono">{fmt(rep.accrued)}</td>
              <td className="print-td-mono">{fmt(rep.paid)}</td>
              <td className={`print-td-bold-mono ${rep.pending > 0 ? 'print-accent' : 'print-text-muted'}`}>{fmt(rep.pending)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="print-tfoot-row">
            <td className="print-td">Total</td>
            <td></td><td></td>
            <td className="print-td-r">{total_invoices}</td>
            <td className="print-td-mono">{fmt(total_sales)}</td>
            <td className="print-td-bold-mono">{fmt(total_commission)}</td>
            <td></td><td></td><td></td>
          </tr>
        </tfoot>
      </table>

      <ApprovalBlock data={data} />
      <Footer company={company} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual Rep Statement
// ---------------------------------------------------------------------------

function RepStatement({ data }: { data: CommissionReportData }) {
  const { company, reps, period_label } = data;
  const rep = reps[0];
  if (!rep) return <div>No commission data for this rep in this period.</div>;

  const detail = rep.detail || [];
  // Aggregate of server-provided detail values — no server-side detail aggregate available
  const totalCredited = detail.reduce((s, d) => s + d.credited, 0);
  const totalComm = detail.reduce((s, d) => s + d.commission, 0);

  return (
    <div className="print-page">
      <Header company={company} title="Commission Statement" periodLabel={period_label} data={data} />

      {/* Rep info */}
      <div className="print-box-highlight print-mb-xl">
        <div className="print-bold print-text-xl">{rep.name}</div>
        <div className="print-text-sm print-text-muted">
          {rep.rep_ida} · {rep.basis} · Base rate: {rep.rate_pct}% · {rep.invoice_count} invoices
        </div>
      </div>

      {/* Invoice detail */}
      <table className="print-table-lg">
        <thead>
          <tr className="print-thead-row">
            <th className="print-th">invoice</th>
            <th className="print-th">date</th>
            <th className="print-th">customer</th>
            <th className="print-th-r">sale</th>
            <th className="print-th-r">credited</th>
            <th className="print-th-r">rate</th>
            <th className="print-th-r">eff rate</th>
            <th className="print-th-r">commission</th>
            <th className="print-th-c">accrued</th>
          </tr>
        </thead>
        <tbody>
          {detail.map((d, i) => (
            <tr key={i} className="print-row">
              <td className="print-td print-medium">{d.invoice_ida}</td>
              <td className="print-td print-text-sm">{d.date}</td>
              <td className="print-td">{d.customer}</td>
              <td className="print-td-mono">{fmt(d.sale_amount)}</td>
              <td className="print-td-mono">{fmt(d.credited)}</td>
              <td className="print-td-r">{formatPercent(d.rate_pct)}</td>
              <td className="print-td-r">{formatPercent(d.effective_rate || 0, 2)}</td>
              <td className="print-td-bold-mono">{fmt(d.commission)}</td>
              <td className="print-td print-center print-text-sm">{d.accrued ? '✓' : '—'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="print-tfoot-row">
            <td className="print-td">Total</td>
            <td></td><td></td>
            <td></td>
            <td className="print-td-mono">{fmt(totalCredited)}</td>
            <td></td><td></td>
            <td className="print-td-bold-mono">{fmt(totalComm)}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>

      {/* Summary box */}
      <div className="print-flex print-gap-md print-mb-3xl">
        <SummaryBox label="Commission Earned" value={fmt(rep.commission_earned)} />
        <SummaryBox label="Accrued (GL posted)" value={fmt(rep.accrued)} />
        <SummaryBox label="Paid" value={fmt(rep.paid)} />
        <SummaryBox label="Pending" value={fmt(rep.pending)} highlight={rep.pending > 0} />
      </div>

      <ApprovalBlock data={data} />
      <Footer company={company} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

function Header({ company, title, periodLabel, data }: {
  company: CommissionReportData['company']; title: string; periodLabel: string; data: CommissionReportData;
}) {
  return (
    <div className="print-header">
      <div>
        {company.logo_url && <img src={company.logo_url} alt="" className="print-logo" />}
        <div className="print-company-name">{company.name}</div>
        <div>{company.address}</div>
        <div>{company.city_state_zip}</div>
        <div>{company.phone}</div>
      </div>
      <div className="print-right">
        <div className="print-text-title">{title}</div>
        <div className="print-text-2xl print-text-subtle">{periodLabel}</div>
        <div className="print-text-sm print-text-dim">{data.period_start} to {data.period_end}</div>
      </div>
    </div>
  );
}

function SummaryBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="print-box-summary">
      <div className="print-text-xs print-text-dim print-mb-xs">{label}</div>
      <div className={`print-text-3xl print-bold print-mono ${highlight ? 'print-accent' : 'print-text'}`}>{value}</div>
    </div>
  );
}

function ApprovalBlock({ data }: { data: CommissionReportData }) {
  return (
    <div className="print-box-padded print-mb-3xl">
      <div className="print-semibold print-mb-md">Approval</div>
      <div className="print-text-sm print-mb-lg">
        Commission amounts shown are based on invoiced sales during {data.period_start} to {data.period_end}.
        Accrued amounts have been posted to the general ledger. Pending amounts await payment.
      </div>
      <div className="print-flex print-gap-lg">
        <div>
          <div className="print-sig-line print-sig-line-md">&nbsp;</div>
          <div className="print-text-xs print-text-dim">Approved By</div>
        </div>
        <div>
          <div className="print-sig-line print-sig-line-sm">&nbsp;</div>
          <div className="print-text-xs print-text-dim">Date</div>
        </div>
      </div>
    </div>
  );
}

function Footer({ company }: { company: CommissionReportData['company'] }) {
  return (
    <div className="print-footer">
      Generated by {company.name} · {formatDt(new Date(), 'date')}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export — picks mode based on data
// ---------------------------------------------------------------------------

export default function CommissionReportPrintDocument({ data }: { data: CommissionReportData }) {
  if (data.rep_name || (data.reps.length === 1 && data.reps[0]?.detail?.length)) {
    return <div data-wc="commission-report-print-document"><RepStatement data={data} /></div>;
  }
  return <div data-wc="commission-report-print-document"><CompanySummary data={data} /></div>;
}
