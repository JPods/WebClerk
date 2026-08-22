/**
 * InvoiceStandardPrint — WC2 "Invoice 1 - Standard" layout.
 *
 * Heritage: James Technologies / CMA invoice format (2002-2014).
 * Features: Ord/Ship/B-O columns, bordered empty rows, serial numbers,
 * Amount/Tax/Freight/Total/Balance Due, finance charge footer.
 */
import React from 'react';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import type { PrintParty, PaperSize } from './printTypes';
import { formatCurrency, formatDate, PAPER_DIMENSIONS } from './printTypes';

export interface InvoiceStandardData {
  id: number;
  ida?: string;
  invoiceNum?: string;
  orderNum?: string;
  status?: string;
  customerID?: number | string;
  // Party
  billTo?: PrintParty;
  shipTo?: PrintParty;
  // Meta
  dateInvoiced?: string;
  dateOrdered?: string;
  dateShipped?: string;
  terms?: string;
  custPONum?: string;
  salesId?: string;
  repId?: string;
  shipVia?: string;
  fob?: string;
  typeSale?: string;
  jobNumber?: string;
  // Lines
  lines?: InvoiceStandardLine[];
  // Financials — JSON envelope is source of truth
  totals?: Record<string, number>;
  // Comments
  comment?: string;
  serialNumbers?: string;
  financeChargeNote?: string;
}

export interface InvoiceStandardLine {
  itemNum?: string;
  description?: string;
  qtyOrdered?: number;
  qtyShipped?: number;
  qtyBackordered?: number;
  unitPrice?: number;
  discountPct?: number;
  extendedPrice?: number;
}

function partyLines(p?: PrintParty): string[] {
  if (!p) return [];
  const lines: string[] = [];
  const name = [p.firstName, p.lastName].filter(Boolean).join(' ') || p.name;
  if (name) lines.push(name);
  if (p.company) lines.push(p.company);
  if (p.address1) lines.push(p.address1);
  if (p.address2) lines.push(p.address2);
  const csz = [p.city, p.state].filter(Boolean).join(', ') + (p.zip ? ` ${p.zip}` : '');
  if (csz.trim()) lines.push(csz.trim());
  if (p.country && p.country !== 'US' && p.country !== 'USA') lines.push(p.country);
  return lines;
}

export default function InvoiceStandardPrint({
  data,
  paperSize = 'letter',
  logoUrl,
}: {
  data: InvoiceStandardData;
  paperSize?: PaperSize;
  logoUrl?: string;
}) {
  const { company } = useDefaultCompany();
  const dims = PAPER_DIMENSIONS[paperSize];
  const resolvedLogo = logoUrl || (company as any)?.logoUrl || '/images/logo/webclerk.png';
  const coName = company?.name || '';
  const coAddr = (company as any)?.address_full || company?.address?.line1 || '';
  const coPhone = (company as any)?.phone || '';
  const coFax = (company as any)?.fax || '';
  const docNum = data.invoiceNum || data.ida || String(data.id);
  const lines = data.lines || [];
  const minRows = 12;

  return (
    <div
      className="print-document bg-white text-black font-sans"
      style={{ width: dims.width, minHeight: dims.height, padding: '0.5in 0.6in', boxSizing: 'border-box', fontSize: 10 }}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-2 pb-2 border-b-2 border-black">
        <div>
          <img src={resolvedLogo} alt={coName} style={{ maxHeight: 44, maxWidth: 180, objectFit: 'contain' }} />
          <div className="text-[8px] text-gray-600 mt-1">
            {coAddr}{coPhone && ` • Phone: ${coPhone}`}{coFax && ` • FAX: ${coFax}`}
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg">Invoice</div>
          <div className="text-xl font-bold">{docNum}</div>
        </div>
      </div>

      {/* Bill To / Ship To + Meta Grid */}
      <div className="flex gap-0 mb-3 border border-gray-400 text-[9px]">
        {/* Bill To */}
        <div className="flex-1 p-2 border-r border-gray-300">
          <div className="text-[8px] text-gray-500 font-semibold mb-1">Bill To:</div>
          {partyLines(data.billTo).map((l, i) => <div key={i}>{l}</div>)}
          {data.billTo?.phone && <div className="mt-1">Phone: {data.billTo.phone}</div>}
        </div>
        {/* Ship To */}
        <div className="flex-1 p-2 border-r border-gray-300">
          <div className="text-[8px] text-gray-500 font-semibold mb-1">Ship To:</div>
          {partyLines(data.shipTo).map((l, i) => <div key={i}>{l}</div>)}
        </div>
        {/* Meta */}
        <div className="p-2" style={{ minWidth: 200 }}>
          <table className="w-full text-[9px]">
            <tbody>
              <tr><td className="text-gray-500 pr-2">Date</td><td className="font-semibold">{formatDate(data.dateInvoiced || data.dateOrdered)}</td></tr>
              <tr><td className="text-gray-500 pr-2">Terms</td><td>{data.terms}</td></tr>
              {data.dateOrdered && <tr><td className="text-gray-500 pr-2">Ordered</td><td>{formatDate(data.dateOrdered)}</td></tr>}
              {data.orderNum && <tr><td className="text-gray-500 pr-2">Order #</td><td>{data.orderNum}</td></tr>}
              <tr><td className="text-gray-500 pr-2">Account #</td><td>{data.customerID}</td></tr>
              {data.custPONum && <tr><td className="text-gray-500 pr-2">Cust PO #</td><td>{data.custPONum}</td></tr>}
              {data.salesId && <tr><td className="text-gray-500 pr-2">Sales</td><td>{data.salesId}</td></tr>}
              {data.repId && <tr><td className="text-gray-500 pr-2">Rep</td><td>{data.repId}</td></tr>}
              {data.shipVia && <tr><td className="text-gray-500 pr-2">Ship Via</td><td>{data.shipVia}</td></tr>}
              {data.fob && <tr><td className="text-gray-500 pr-2">FOB</td><td>{data.fob}</td></tr>}
              {data.typeSale && <tr><td className="text-gray-500 pr-2">Type Sale</td><td>{data.typeSale}</td></tr>}
              {data.jobNumber && <tr><td className="text-gray-500 pr-2">Job</td><td>{data.jobNumber}</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* Line Items — Ord/Ship/B-O columns */}
      <table className="w-full text-[9px] border-collapse border border-gray-400 mb-3">
        <thead>
          <tr className="bg-gray-100 border-b-2 border-gray-500">
            <th className="border border-gray-300 px-1 py-1 text-left w-20">Item Num</th>
            <th className="border border-gray-300 px-1 py-1 text-left">Description</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-10">Ord</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-10">Ship</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-10">B/O</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-16">Unit Price</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-12">% Disc.</th>
            <th className="border border-gray-300 px-1 py-1 text-right w-18">Ext Price</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((ln, i) => (
            <tr key={i} className="border-b border-gray-200 avoid-break">
              <td className="border border-gray-200 px-1 py-1">{ln.itemNum}</td>
              <td className="border border-gray-200 px-1 py-1">{ln.description}</td>
              <td className="border border-gray-200 px-1 py-1 text-right">{ln.qtyOrdered}</td>
              <td className="border border-gray-200 px-1 py-1 text-right">{ln.qtyShipped}</td>
              <td className="border border-gray-200 px-1 py-1 text-right">{ln.qtyBackordered || 0}</td>
              <td className="border border-gray-200 px-1 py-1 text-right">{formatCurrency(ln.unitPrice)}</td>
              <td className="border border-gray-200 px-1 py-1 text-right">
                {(ln.discountPct || 0) > 0 ? `${ln.discountPct?.toFixed(1)}` : '0.0'}
              </td>
              <td className="border border-gray-200 px-1 py-1 text-right">{formatCurrency(ln.extendedPrice)}</td>
            </tr>
          ))}
          {/* Empty bordered rows (WC2 physical form feel) */}
          {Array.from({ length: Math.max(0, minRows - lines.length) }).map((_, i) => (
            <tr key={`e-${i}`} style={{ height: 18 }}>
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
              <td className="border border-gray-200 px-1 py-1" />
            </tr>
          ))}
        </tbody>
      </table>

      {/* Comments + Serial Numbers + Totals */}
      <div className="flex gap-4 mb-3">
        <div className="flex-1 text-[9px] border border-gray-300 p-2">
          {data.serialNumbers && (
            <div className="mb-2">
              <span className="font-semibold">Serial Numbers: </span>{data.serialNumbers}
            </div>
          )}
          {data.comment && <div className="whitespace-pre-wrap">{data.comment}</div>}
        </div>
        <div className="w-52 text-[10px]">
          <table className="w-full">
            <tbody>
              <tr><td className="py-0.5 text-right pr-3">Amount</td><td className="py-0.5 text-right">{formatCurrency(data.totals?.subtotal)}</td></tr>
              <tr><td className="py-0.5 text-right pr-3">Tax</td><td className="py-0.5 text-right">{formatCurrency(data.totals?.tax ?? 0)}</td></tr>
              <tr><td className="py-0.5 text-right pr-3">Freight</td><td className="py-0.5 text-right">{formatCurrency(data.totals?.shipping ?? 0)}</td></tr>
              <tr className="border-t border-gray-400 font-semibold">
                <td className="py-1 text-right pr-3">Invoice Total</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.total)}</td>
              </tr>
              <tr className="font-semibold">
                <td className="py-0.5 text-right pr-3">Balance Due</td>
                <td className="py-0.5 text-right">{formatCurrency(data.totals?.balance)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Finance charge footer */}
      <div className="text-[8px] text-gray-500 border-t border-gray-300 pt-2">
        {data.financeChargeNote || 'A finance charge of 1.5% per month will be charged on all overdue balances.'}
      </div>
    </div>
  );
}
