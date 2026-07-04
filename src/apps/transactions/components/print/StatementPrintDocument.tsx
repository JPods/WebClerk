/**
 * StatementPrintDocument — customer statement matching WC2 format.
 *
 * Shows: company header, customer info, urgency message, response area,
 * aging summary (balance due / current / 1-30 / 31-60 / 61+),
 * transaction detail (type / number / date / total / balance / aging / finance / days).
 *
 * Data source: POST /wcapi/manage/ { action: "get_customer_statement", params: { customer_id } }
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
    <div className="print-page" style={{ fontFamily: 'Helvetica, Arial, sans-serif', fontSize: 11, color: '#222', padding: '0.5in 0.75in' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          {company.logo_url && <img src={company.logo_url} alt="" style={{ maxHeight: 50, marginBottom: 8 }} />}
          <div style={{ fontWeight: 700, fontSize: 14 }}>{company.name}</div>
          <div>{company.address}</div>
          <div>{company.city_state_zip}</div>
          <div>{company.phone}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 22, fontWeight: 700 }}>Statement: {statement_date}</div>
          <div style={{ color: '#666' }}>{company.name}</div>
        </div>
      </div>

      {/* Customer + Message */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16, border: '1px solid #ccc', padding: 12 }}>
        <div style={{ flex: 1 }}>
          {customer.attention && <div><strong>Attention:</strong> {customer.attention}</div>}
          {customer.company && <div><strong>Company:</strong> {customer.company}</div>}
          {customer.address1 && <div>{customer.address1}</div>}
          {customer.address2 && <div>{customer.address2}</div>}
          <div>{[customer.city, customer.state].filter(Boolean).join(', ')} {customer.zip}</div>
          {customer.phone && <div><strong>Phone:</strong> {customer.phone}</div>}
          {customer.email && <div><strong>Fax:</strong> {customer.email}</div>}
        </div>
        <div style={{ flex: 1, borderLeft: '1px solid #ccc', paddingLeft: 16 }}>
          <div style={{ fontSize: 10, marginBottom: 8 }}>
            {message || 'Our records show that we have yet to receive payments for the invoice(s) list below. These invoices are critically overdue. Immediate payment is required to maintain our business relationship.'}
          </div>
          <div style={{ fontSize: 10, borderTop: '1px solid #ccc', paddingTop: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Response Area</div>
            <div>○ The check is in the mail.</div>
            <div>○ I don't have copies of invoices. (✓ needed invoices)</div>
            <div>○ Payment is due to be mailed on ____________.</div>
            <div>○ Other: ______________________________________</div>
          </div>
        </div>
      </div>

      {/* Aging Summary */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #000' }}>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}></th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Balance Due</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Current</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>1 to 30 Days<br/>Past Due</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>31 to 60 Days<br/>Past Due</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>61+ Days<br/>Past Due</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ borderBottom: '1px solid #ccc', fontWeight: 700 }}>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>Totals:</td>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(aging.balance_due)}</td>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(aging.current)}</td>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(aging.past_1_30)}</td>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(aging.past_31_60)}</td>
            <td style={{ textAlign: 'right', padding: '4px 8px' }}>{fmt(aging.past_61)}</td>
          </tr>
        </tbody>
      </table>

      {/* Transaction Details */}
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 4 }}>Transaction Details:</div>
      <div style={{ fontSize: 9, color: '#666', marginBottom: 4 }}>- - - - - - - - - Transaction - - - - - - - - -</div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #000' }}>
            <th style={{ textAlign: 'left', padding: '3px 4px' }}>Type</th>
            <th style={{ textAlign: 'left', padding: '3px 4px' }}>Number</th>
            <th style={{ textAlign: 'left', padding: '3px 4px' }}>Date</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>Total</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>Balance</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>Current</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>1-30</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>31-60</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>61+</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>Finance</th>
            <th style={{ textAlign: 'right', padding: '3px 4px' }}>Days</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '3px 4px' }}>{line.type}</td>
              <td style={{ padding: '3px 4px' }}>{line.number}</td>
              <td style={{ padding: '3px 4px' }}>{line.date}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.total)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.balance)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.current)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.past_1_30)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.past_31_60)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.past_61)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{fmt(line.finance)}</td>
              <td style={{ textAlign: 'right', padding: '3px 4px' }}>{line.days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
