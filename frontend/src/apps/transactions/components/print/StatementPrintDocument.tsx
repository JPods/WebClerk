/**
 * StatementPrintDocument — customer statement matching WC2 format.
 *
 * Shows: company header, customer info, urgency message, response area,
 * aging summary (balance due / current / 1-30 / 31-60 / 61+),
 * transaction detail (type / number / date / total / balance / aging / finance / days).
 *
 * Data source: POST /wcapi/_manage/ { action: "get_customer_statement", params: { customer_id } }
 * Print: window.print() with print.css
 */
import React from 'react';
import type { PrintParty } from './printTypes';
import { formatCurrency, formatDate } from './printTypes';

export interface StatementLine {
  type: string;           // 'Inv', 'Pay', 'CM'
  number: string;         // invoice/payment ida
  date: string;           // formatted date
  total: number;          // original amount
  balance: number;        // remaining balance
  current: number;
  past_1_30: number;
  past_31_60: number;
  past_61: number;
  finance: number;        // accumulated finance charges
  days: number;           // days past due
}

export interface StatementData {
  statement_date: string;
  company: {
    name: string;
    address: string;
    city_state_zip: string;
    phone: string;
    logo_url?: string;
  };
  customer: PrintParty;
  aging_summary: {
    balance_due: number;
    current: number;
    past_1_30: number;
    past_31_60: number;
    past_61: number;
  };
  lines: StatementLine[];
  message?: string;
}

const fmt = (n: number) => n !== 0 ? formatCurrency(n) : '0.00';

export default function StatementPrintDocument({ data }: { data: StatementData }) {
  const { company, customer, aging_summary: aging, lines, statement_date, message } = data;

  return (
    <div data-wc="statement-print-document" className="print-page">

      {/* Header */}
      <div className="print-header-plain">
        <div>
          {company.logo_url && <img src={company.logo_url} alt="" className="print-logo" />}
          <div className="print-company-name">{company.name}</div>
          <div>{company.address}</div>
          <div>{company.city_state_zip}</div>
          <div>{company.phone}</div>
        </div>
        <div className="print-right">
          <div className="print-text-title-lg">Statement: {statement_date}</div>
          <div className="print-text-muted">{company.name}</div>
        </div>
      </div>

      {/* Customer + Message */}
      <div className="print-box print-flex print-gap-sm print-mb-xl">
        <div className="print-flex-1">
          {customer.attention && <div><strong>Attention:</strong> {customer.attention}</div>}
          {customer.company && <div><strong>Company:</strong> {customer.company}</div>}
          {customer.address1 && <div>{customer.address1}</div>}
          {customer.address2 && <div>{customer.address2}</div>}
          <div>{[customer.city, customer.state].filter(Boolean).join(', ')} {customer.zip}</div>
          {customer.phone && <div><strong>Phone:</strong> {customer.phone}</div>}
          {customer.email && <div><strong>Fax:</strong> {customer.email}</div>}
        </div>
        <div className="print-flex-1 print-border-left">
          <div className="print-text-sm print-mb-md">
            {message || 'Our records show that we have yet to receive payments for the invoice(s) list below. These invoices are critically overdue. Immediate payment is required to maintain our business relationship.'}
          </div>
          <div className="print-text-sm print-border-top">
            <div className="print-semibold print-mb-sm">Response Area</div>
            <div>○ The check is in the mail.</div>
            <div>○ I don't have copies of invoices. (✓ needed invoices)</div>
            <div>○ Payment is due to be mailed on ____________.</div>
            <div>○ Other: ______________________________________</div>
          </div>
        </div>
      </div>

      {/* Aging Summary */}
      <table className="print-table">
        <thead>
          <tr className="print-thead-row">
            <th className="print-td-aging"></th>
            <th className="print-td-aging">Balance Due</th>
            <th className="print-td-aging">Current</th>
            <th className="print-td-aging">1 to 30 Days<br/>Past Due</th>
            <th className="print-td-aging">31 to 60 Days<br/>Past Due</th>
            <th className="print-td-aging">61+ Days<br/>Past Due</th>
          </tr>
        </thead>
        <tbody>
          <tr className="print-row print-bold">
            <td className="print-td-aging">Totals:</td>
            <td className="print-td-aging">{fmt(aging.balance_due)}</td>
            <td className="print-td-aging">{fmt(aging.current)}</td>
            <td className="print-td-aging">{fmt(aging.past_1_30)}</td>
            <td className="print-td-aging">{fmt(aging.past_31_60)}</td>
            <td className="print-td-aging">{fmt(aging.past_61)}</td>
          </tr>
        </tbody>
      </table>

      {/* Transaction Details */}
      <div className="print-bold print-text-lg print-mb-sm">Transaction Details:</div>
      <div className="print-text-xs print-text-muted print-mb-sm">- - - - - - - - - Transaction - - - - - - - - -</div>

      <table className="print-table-detail">
        <thead>
          <tr className="print-row">
            <th className="print-th-compact">Type</th>
            <th className="print-th-compact">Number</th>
            <th className="print-th-compact">Date</th>
            <th className="print-th-compact-r">Total</th>
            <th className="print-th-compact-r">Balance</th>
            <th className="print-th-compact-r">Current</th>
            <th className="print-th-compact-r">1-30</th>
            <th className="print-th-compact-r">31-60</th>
            <th className="print-th-compact-r">61+</th>
            <th className="print-th-compact-r">Finance</th>
            <th className="print-th-compact-r">Days</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr key={i} className="print-row-light">
              <td className="print-td-compact">{line.type}</td>
              <td className="print-td-compact">{line.number}</td>
              <td className="print-td-compact">{line.date}</td>
              <td className="print-td-compact-r">{fmt(line.total)}</td>
              <td className="print-td-compact-r">{fmt(line.balance)}</td>
              <td className="print-td-compact-r">{fmt(line.current)}</td>
              <td className="print-td-compact-r">{fmt(line.past_1_30)}</td>
              <td className="print-td-compact-r">{fmt(line.past_31_60)}</td>
              <td className="print-td-compact-r">{fmt(line.past_61)}</td>
              <td className="print-td-compact-r">{fmt(line.finance)}</td>
              <td className="print-td-compact-r">{line.days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
