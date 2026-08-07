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

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const PAGE: React.CSSProperties = {
  fontFamily: 'Helvetica, Arial, sans-serif', fontSize: 11, color: '#222', padding: '0.5in 0.75in',
};
const TH: React.CSSProperties = { textAlign: 'left', padding: '6px 8px', fontSize: 11 };
const TH_R: React.CSSProperties = { ...TH, textAlign: 'right' };
const TH_C: React.CSSProperties = { ...TH, textAlign: 'center' };
const TD: React.CSSProperties = { padding: '5px 8px' };
const TD_R: React.CSSProperties = { ...TD, textAlign: 'right' };
const TD_MONO: React.CSSProperties = { ...TD_R, fontFamily: 'monospace' };
const BOLD_MONO: React.CSSProperties = { ...TD_MONO, fontWeight: 600 };

const fmt = (n: number) => formatCurrency(n);

// ---------------------------------------------------------------------------
// Company Summary
// ---------------------------------------------------------------------------

function CompanySummary({ data }: { data: CommissionReportData }) {
  const { company, reps, period_label, total_sales, total_commission, total_invoices } = data;

  return (
    <div className="print-page" style={PAGE}>
      <Header company={company} title="Commission Report" periodLabel={period_label} data={data} />

      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #000' }}>
            <th style={TH}>Representative</th>
            <th style={TH_C}>Basis</th>
            <th style={TH_R}>Rate</th>
            <th style={TH_R}>Invoices</th>
            <th style={TH_R}>Sales Credited</th>
            <th style={TH_R}>Commission</th>
            <th style={TH_R}>Accrued</th>
            <th style={TH_R}>Paid</th>
            <th style={TH_R}>Pending</th>
          </tr>
        </thead>
        <tbody>
          {reps.map((rep, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #ddd' }}>
              <td style={TD}>
                <div style={{ fontWeight: 600 }}>{rep.name}</div>
                <div style={{ fontSize: 9, color: '#888' }}>{rep.rep_ida}</div>
              </td>
              <td style={{ ...TD, textAlign: 'center', fontSize: 10 }}>{rep.basis}</td>
              <td style={TD_R}>{rep.rate_pct.toFixed(1)}%</td>
              <td style={TD_R}>{rep.invoice_count}</td>
              <td style={TD_MONO}>{fmt(rep.sales_credited)}</td>
              <td style={BOLD_MONO}>{fmt(rep.commission_earned)}</td>
              <td style={TD_MONO}>{fmt(rep.accrued)}</td>
              <td style={TD_MONO}>{fmt(rep.paid)}</td>
              <td style={{ ...BOLD_MONO, color: rep.pending > 0 ? '#9333ea' : '#666' }}>{fmt(rep.pending)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid #000', fontWeight: 700 }}>
            <td style={TD}>Total</td>
            <td></td><td></td>
            <td style={TD_R}>{total_invoices}</td>
            <td style={TD_MONO}>{fmt(total_sales)}</td>
            <td style={BOLD_MONO}>{fmt(total_commission)}</td>
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
  const totalCredited = detail.reduce((s, d) => s + d.credited, 0);
  const totalComm = detail.reduce((s, d) => s + d.commission, 0);

  return (
    <div className="print-page" style={PAGE}>
      <Header company={company} title="Commission Statement" periodLabel={period_label} data={data} />

      {/* Rep info */}
      <div style={{ marginBottom: 16, padding: '8px 12px', background: '#f8f8f8', border: '1px solid #ddd' }}>
        <div style={{ fontWeight: 700, fontSize: 13 }}>{rep.name}</div>
        <div style={{ fontSize: 10, color: '#666' }}>
          {rep.rep_ida} · {rep.basis} · Base rate: {rep.rate_pct}% · {rep.invoice_count} invoices
        </div>
      </div>

      {/* Invoice detail */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #000' }}>
            <th style={TH}>Invoice</th>
            <th style={TH}>Date</th>
            <th style={TH}>Customer</th>
            <th style={TH_R}>Sale</th>
            <th style={TH_R}>Credited</th>
            <th style={TH_R}>Rate</th>
            <th style={TH_R}>Eff Rate</th>
            <th style={TH_R}>Commission</th>
            <th style={TH_C}>Accrued</th>
          </tr>
        </thead>
        <tbody>
          {detail.map((d, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #ddd' }}>
              <td style={{ ...TD, fontWeight: 500 }}>{d.invoice_ida}</td>
              <td style={{ ...TD, fontSize: 10 }}>{d.date}</td>
              <td style={TD}>{d.customer}</td>
              <td style={TD_MONO}>{fmt(d.sale_amount)}</td>
              <td style={TD_MONO}>{fmt(d.credited)}</td>
              <td style={TD_R}>{d.rate_pct.toFixed(1)}%</td>
              <td style={TD_R}>{(d.effective_rate || 0).toFixed(2)}%</td>
              <td style={BOLD_MONO}>{fmt(d.commission)}</td>
              <td style={{ ...TD, textAlign: 'center', fontSize: 10 }}>{d.accrued ? '✓' : '—'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid #000', fontWeight: 700 }}>
            <td style={TD}>Total</td>
            <td></td><td></td>
            <td></td>
            <td style={TD_MONO}>{fmt(totalCredited)}</td>
            <td></td><td></td>
            <td style={BOLD_MONO}>{fmt(totalComm)}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>

      {/* Summary box */}
      <div style={{ display: 'flex', gap: 32, marginBottom: 24 }}>
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
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20, borderBottom: '2px solid #000', paddingBottom: 12 }}>
      <div>
        {company.logo_url && <img src={company.logo_url} alt="" style={{ maxHeight: 50, marginBottom: 8 }} />}
        <div style={{ fontWeight: 700, fontSize: 14 }}>{company.name}</div>
        <div>{company.address}</div>
        <div>{company.city_state_zip}</div>
        <div>{company.phone}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 20, fontWeight: 700 }}>{title}</div>
        <div style={{ fontSize: 14, color: '#444' }}>{periodLabel}</div>
        <div style={{ fontSize: 10, color: '#888' }}>{data.period_start} to {data.period_end}</div>
      </div>
    </div>
  );
}

function SummaryBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '8px 16px', minWidth: 120 }}>
      <div style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'monospace', color: highlight ? '#9333ea' : '#222' }}>{value}</div>
    </div>
  );
}

function ApprovalBlock({ data }: { data: CommissionReportData }) {
  return (
    <div style={{ border: '1px solid #ccc', padding: 16, marginBottom: 24 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Approval</div>
      <div style={{ fontSize: 10, marginBottom: 12 }}>
        Commission amounts shown are based on invoiced sales during {data.period_start} to {data.period_end}.
        Accrued amounts have been posted to the general ledger. Pending amounts await payment.
      </div>
      <div style={{ display: 'flex', gap: 48 }}>
        <div>
          <div style={{ borderBottom: '1px solid #000', width: 200, marginBottom: 4 }}>&nbsp;</div>
          <div style={{ fontSize: 9, color: '#888' }}>Approved By</div>
        </div>
        <div>
          <div style={{ borderBottom: '1px solid #000', width: 120, marginBottom: 4 }}>&nbsp;</div>
          <div style={{ fontSize: 9, color: '#888' }}>Date</div>
        </div>
      </div>
    </div>
  );
}

function Footer({ company }: { company: CommissionReportData['company'] }) {
  return (
    <div style={{ fontSize: 9, color: '#888', textAlign: 'center' }}>
      Generated by {company.name} · {new Date().toLocaleDateString()}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export — picks mode based on data
// ---------------------------------------------------------------------------

export default function CommissionReportPrintDocument({ data }: { data: CommissionReportData }) {
  if (data.rep_name || (data.reps.length === 1 && data.reps[0]?.detail?.length)) {
    return <RepStatement data={data} />;
  }
  return <CompanySummary data={data} />;
}
