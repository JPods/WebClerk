/**
 * InvoiceServicePrint — JIT/JPods service invoice layout.
 *
 * Heritage: JIT Corp / JPods LLC invoice (2014-2026).
 * Features: Company block top-left, Web/Email/Phone center-top,
 * Invoice title italic top-right, Job# field, Instructions field,
 * Shipped/Ordered/Bk-Ord columns, simple "Total Due" for international,
 * ACH/wire payment info in comments.
 */
import React from 'react';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import type { PrintParty, PaperSize } from './printTypes';
import { formatCurrency, formatDate, PAPER_DIMENSIONS } from './printTypes';

export interface InvoiceServiceData {
  id: number;
  ida?: string;
  invoiceNum?: string;
  orderNum?: string;
  status?: string;
  customerID?: number | string;
  // Party
  billTo?: PrintParty;
  shipTo?: PrintParty;
  customerPhone?: string;
  customerFax?: string;
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
  instructions?: string;
  // Lines
  lines?: InvoiceServiceLine[];
  // Totals — can use simple or detailed
  salesAmount?: number;
  salesTax?: number;
  shipping?: number;
  total?: number;
  balanceDue?: number;
  simpleTotal?: boolean; // true = show only "Total Due"
  // Comments
  comment?: string;
}

export interface InvoiceServiceLine {
  itemNum?: string;
  description?: string;
  qtyShipped?: number;
  qtyOrdered?: number;
  qtyBackordered?: number;
  taxable?: string; // 'T' flag
  unitPrice?: number;
  extendedPrice?: number;
}

function partyLines(p?: PrintParty): string[] {
  if (!p) return [];
  const out: string[] = [];
  const name = [p.firstName, p.lastName].filter(Boolean).join(' ') || p.name;
  if (name) out.push(name);
  if (p.company) out.push(p.company);
  if (p.address1) out.push(p.address1);
  if (p.address2) out.push(p.address2);
  const csz = [p.city, p.state].filter(Boolean).join(', ') + (p.zip ? ` ${p.zip}` : '');
  if (csz.trim()) out.push(csz.trim());
  if (p.country && !['US', 'USA'].includes(p.country)) out.push(p.country);
  return out;
}

export default function InvoiceServicePrint({
  data,
  paperSize = 'letter',
  logoUrl,
}: {
  data: InvoiceServiceData;
  paperSize?: PaperSize;
  logoUrl?: string;
}) {
  const { company } = useDefaultCompany();
  const dims = PAPER_DIMENSIONS[paperSize];
  const resolvedLogo = logoUrl || (company as any)?.logoUrl || '/images/logo/webclerk.png';
  const coName = company?.name || '';
  const coAddr = (company as any)?.address_full || '';
  const coPhone = (company as any)?.phone || '';
  const coEmail = (company as any)?.email || '';
  const coWeb = (company as any)?.website || '';
  const docNum = data.invoiceNum || data.ida || String(data.id);
  const lines = data.lines || [];

  return (
    <div
      className="print-document bg-white text-black font-sans"
      style={{ width: dims.width, minHeight: dims.height, padding: '0.5in 0.6in', boxSizing: 'border-box', fontSize: 10 }}
    >
      {/* Header: Company left, Web/Email/Phone center, Invoice right */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <img src={resolvedLogo} alt={coName} style={{ maxHeight: 50, maxWidth: 180, objectFit: 'contain' }} />
          <div className="font-bold text-sm mt-1">{coName}</div>
          <div className="text-[9px]">{coAddr}</div>
        </div>
        <div className="text-[9px]">
          {coWeb && <div><span className="text-gray-500 w-12 inline-block">Web</span> {coWeb}</div>}
          {coEmail && <div><span className="text-gray-500 w-12 inline-block">E-mail</span> {coEmail}</div>}
          {coPhone && <div><span className="text-gray-500 w-12 inline-block">Phone</span> {coPhone}</div>}
        </div>
        <div className="text-right">
          <div className="text-xl italic font-bold">Invoice</div>
          <div className="text-2xl font-bold">{docNum}</div>
        </div>
      </div>

      {/* Bill To + Ship To + Meta Grid (2-column boxed) */}
      <div className="flex gap-4 mb-3">
        {/* Left: Addresses */}
        <div className="text-[9px]" style={{ minWidth: 200 }}>
          <div className="italic text-gray-600 mb-1">Bill To:</div>
          {partyLines(data.billTo).map((l, i) => <div key={i} className="ml-2">{l}</div>)}
          {data.billTo && <div className="h-2" />}
          <div className="italic text-gray-600 mb-1">Ship To:</div>
          {partyLines(data.shipTo).map((l, i) => <div key={i} className="ml-2">{l}</div>)}
          {data.customerPhone && <div className="mt-2"><span className="italic text-gray-600">Customer Phone</span> {data.customerPhone}</div>}
          {data.customerFax && <div><span className="italic text-gray-600">Customer Fax</span> {data.customerFax}</div>}
        </div>

        {/* Right: Meta grid */}
        <div className="flex-1 border border-gray-400 text-[9px]">
          <div className="flex">
            <div className="flex-1 p-1 border-r border-b border-gray-300">
              <span className="italic text-gray-600">Order # </span>
              <span className="font-semibold ml-2">{data.orderNum}</span>
            </div>
            <div className="flex-1 p-1 border-b border-gray-300">
              <span className="italic text-gray-600">Job </span>
              <span className="font-semibold ml-2">{data.jobNumber}</span>
            </div>
          </div>
          <div className="flex">
            <div className="flex-1 p-1 border-r border-b border-gray-300">
              <span className="italic text-gray-600">Shipped </span>
              <span className="ml-2">{formatDate(data.dateShipped) || data.dateShipped}</span>
            </div>
            <div className="flex-1 p-1 border-b border-gray-300">
              <span className="italic text-gray-600">Invoiced </span>
              <span className="ml-2">{formatDate(data.dateInvoiced)}</span>
            </div>
          </div>
          <div className="flex">
            <div className="flex-1 p-1 border-r border-b border-gray-300">
              <span className="italic text-gray-600">Account # </span>
              <span className="ml-2">{data.customerID}</span>
            </div>
            <div className="flex-1 p-1 border-b border-gray-300">
              <span className="italic text-gray-600">Rep </span>
              <span className="ml-2">{data.repId}</span>
            </div>
          </div>
          <div className="flex">
            <div className="flex-1 p-1 border-r border-b border-gray-300">
              <span className="italic text-gray-600">Cust PO # </span>
              <span className="ml-2">{data.custPONum}</span>
            </div>
            <div className="flex-1 p-1 border-b border-gray-300">
              <span className="italic text-gray-600">FOB: </span>
              <span className="ml-2">{data.fob}</span>
            </div>
          </div>
          <div className="flex">
            <div className="flex-1 p-1 border-r border-b border-gray-300">
              <span className="italic text-gray-600">Terms </span>
              <span className="ml-2">{data.terms}</span>
            </div>
            <div className="flex-1 p-1 border-b border-gray-300">
              <span className="italic text-gray-600">Type Sale </span>
              <span className="ml-2">{data.typeSale}</span>
            </div>
          </div>
          <div className="flex">
            <div className="flex-1 p-1 border-r border-gray-300">
              <span className="italic text-gray-600">Sales </span>
              <span className="ml-2">{data.salesId}</span>
            </div>
            <div className="flex-1 p-1" />
          </div>
          <div className="p-1 border-t border-gray-300">
            <span className="italic text-gray-600">Ship Via </span>
            <span className="ml-2">{data.shipVia}</span>
          </div>
          {data.instructions && (
            <div className="p-1 border-t border-gray-300">
              <span className="italic text-gray-600">Instructions </span>
              <span className="ml-2">{data.instructions}</span>
            </div>
          )}
        </div>
      </div>

      {/* Line Items: Shipped | Ordered | Bk/Ord | Item Num | Description | T | Unit Price | Ext Price */}
      <table className="w-full text-[9px] border-collapse mb-4">
        <thead>
          <tr className="border-b border-gray-400">
            <th className="text-right py-1 px-1 w-14">Shipped</th>
            <th className="text-right py-1 px-1 w-14">Ordered</th>
            <th className="text-right py-1 px-1 w-12">Bk/Ord</th>
            <th className="text-left py-1 px-1 w-20">Item Num</th>
            <th className="text-left py-1 px-1">Description</th>
            <th className="text-center py-1 px-1 w-6">T</th>
            <th className="text-right py-1 px-1 w-18">Unit Price</th>
            <th className="text-right py-1 px-1 w-18">Ext Price</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((ln, i) => (
            <tr key={i} className="border-b border-gray-200 avoid-break align-top">
              <td className="py-1 px-1 text-right">{ln.qtyShipped}</td>
              <td className="py-1 px-1 text-right">{ln.qtyOrdered}</td>
              <td className="py-1 px-1 text-right">{ln.qtyBackordered || 0}</td>
              <td className="py-1 px-1">{ln.itemNum}</td>
              <td className="py-1 px-1 whitespace-pre-wrap">{ln.description}</td>
              <td className="py-1 px-1 text-center">{ln.taxable || ''}</td>
              <td className="py-1 px-1 text-right">{formatCurrency(ln.unitPrice)}</td>
              <td className="py-1 px-1 text-right">{formatCurrency(ln.extendedPrice)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Comments + Totals */}
      <div className="flex gap-4 border-t border-gray-400 pt-2">
        <div className="flex-1 text-[9px]">
          {data.comment && (
            <>
              <div className="font-semibold mb-1">Comments:</div>
              <div className="whitespace-pre-wrap">{data.comment}</div>
            </>
          )}
        </div>
        <div className="w-52 text-[10px]">
          {data.simpleTotal ? (
            <table className="w-full">
              <tbody>
                <tr className="font-bold">
                  <td className="py-1 text-right pr-3">Total Due</td>
                  <td className="py-1 text-right">{formatCurrency(data.total || data.balanceDue)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <table className="w-full">
              <tbody>
                <tr><td className="py-0.5 text-right pr-3">Sales Amount</td><td className="py-0.5 text-right">{formatCurrency(data.salesAmount)}</td></tr>
                <tr><td className="py-0.5 text-right pr-3">Tax</td><td className="py-0.5 text-right">{formatCurrency(data.salesTax || 0)}</td></tr>
                <tr><td className="py-0.5 text-right pr-3">Ship/Handling</td><td className="py-0.5 text-right">{formatCurrency(data.shipping || 0)}</td></tr>
                <tr className="font-bold"><td className="py-1 text-right pr-3">Invoice Total</td><td className="py-1 text-right">{formatCurrency(data.total)}</td></tr>
                <tr className="font-bold"><td className="py-0.5 text-right pr-3">Balance Due</td><td className="py-0.5 text-right">{formatCurrency(data.balanceDue)}</td></tr>
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
