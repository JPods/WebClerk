/**
 * InvoiceShippingPrint — WC2 "Invoice 2 - Shipping" / Print3 layout.
 *
 * Heritage: Advanced Chimney Techniques invoice (2020-2021 React iteration).
 * Features: Bill To / Ship To / Contact Us / Customer 4-column header,
 * Invoice Date field, QtyShip/Disc/Unit/Extended columns,
 * DownPayment line, Contract Detail acceptance block.
 */
import React from 'react';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import type { PrintParty, PaperSize } from './printTypes';
import { formatCurrency, formatDate, PAPER_DIMENSIONS } from './printTypes';

export interface InvoiceShippingData {
  id: number;
  ida?: string;
  invoiceNum?: string;
  orderNum?: string;
  status?: string;
  customerID?: number | string;
  // Party
  billTo?: PrintParty;
  shipTo?: PrintParty;
  contactPhone?: string;
  contactCell?: string;
  customerPhone?: string;
  customerCell?: string;
  // Meta
  dateInvoiced?: string;
  dateShipped?: string;
  dateOrdered?: string;
  terms?: string;
  custPONum?: string;
  salesId?: string;
  shipVia?: string;
  fob?: string;
  typeSale?: string;
  orderedBy?: string;
  packedBy?: string;
  // Lines
  lines?: InvoiceShippingLine[];
  // Financials — JSON envelope is source of truth
  totals?: Record<string, number>;
  downPayment?: number;
  // Comments
  comment?: string;
  contractDetail?: string;
}

export interface InvoiceShippingLine {
  itemNum?: string;
  description?: string;
  qtyShipped?: number;
  discountPct?: number;
  unitPrice?: number;
  extendedPrice?: number;
}

function partyLines(p?: PrintParty): string[] {
  if (!p) return [];
  const lines: string[] = [];
  if (p.attention) lines.push(p.attention);
  const name = [p.firstName, p.lastName].filter(Boolean).join(' ') || p.name;
  if (name) lines.push(name);
  if (p.company) lines.push(p.company);
  if (p.address1) lines.push(p.address1);
  if (p.address2) lines.push(p.address2);
  const csz = [p.city, p.state].filter(Boolean).join(', ') + (p.zip ? ` ${p.zip}` : '');
  if (csz.trim()) lines.push(csz.trim());
  if (p.country && !['US', 'USA'].includes(p.country)) lines.push(p.country);
  return lines;
}

export default function InvoiceShippingPrint({
  data,
  paperSize = 'letter',
  logoUrl,
}: {
  data: InvoiceShippingData;
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
      {/* Header: Company info left, Logo center, Title right */}
      <div className="flex justify-between items-start mb-3">
        <div className="text-[9px]">
          {coPhone && <div>{coPhone}</div>}
          {coEmail && <div>{coEmail}</div>}
          {coWeb && <div>{coWeb}</div>}
          {coAddr && <div>{coAddr}</div>}
        </div>
        <div className="text-center">
          <img src={resolvedLogo} alt={coName} style={{ maxHeight: 56, maxWidth: 120, objectFit: 'contain' }} />
        </div>
        <div className="text-right">
          <div className="text-sm">{coName}</div>
          <div className="text-2xl font-bold">INVOICE:</div>
          <div className="text-2xl font-bold">{docNum}</div>
        </div>
      </div>

      {/* 4-Column Address Block */}
      <div className="flex gap-0 mb-2 border border-gray-400 text-[9px]">
        <div className="flex-1 p-2 border-r border-gray-300">
          <div className="text-[8px] text-gray-500 font-semibold">Bill To:</div>
          {partyLines(data.billTo).map((l, i) => <div key={i} className="font-semibold">{l}</div>)}
        </div>
        <div className="flex-1 p-2 border-r border-gray-300">
          <div className="text-[8px] text-gray-500 font-semibold">Ship To:</div>
          {partyLines(data.shipTo).map((l, i) => <div key={i}>{l}</div>)}
        </div>
        <div className="p-2 border-r border-gray-300" style={{ minWidth: 120 }}>
          <div className="text-[8px] text-gray-500 font-semibold">Contact Us:</div>
          {data.contactPhone && <div>Phone: {data.contactPhone}</div>}
          {data.contactCell && <div>Cell: {data.contactCell}</div>}
          <div className="text-[8px] text-gray-500 mt-1">Ship Via:</div>
          <div>{data.shipVia || 'NA'}</div>
        </div>
        <div className="p-2" style={{ minWidth: 130 }}>
          <div className="text-[8px] text-gray-500 font-semibold">Customer:</div>
          {data.customerPhone && <div>Phone: {data.customerPhone}</div>}
          {data.customerCell && <div>Cell: {data.customerCell}</div>}
        </div>
      </div>

      {/* Meta Grid */}
      <div className="grid grid-cols-4 gap-0 mb-3 text-[9px] border border-gray-300">
        <div className="p-1 border-r border-gray-200">
          <span className="text-gray-500">Cust PO# : </span>{data.custPONum}
        </div>
        <div className="p-1 border-r border-gray-200">
          <span className="text-gray-500">Account : </span>{data.customerID}
        </div>
        <div className="p-1 border-r border-gray-200">
          <span className="text-gray-500">Order# : </span>{data.orderNum}
        </div>
        <div className="p-1">
          <span className="text-gray-500">Type Sale : </span>{data.typeSale}
        </div>
        <div className="p-1 border-r border-gray-200 border-t border-gray-200">
          <span className="text-gray-500">Invoice Date : </span>{formatDate(data.dateInvoiced)}
        </div>
        <div className="p-1 border-r border-gray-200 border-t border-gray-200">
          <span className="text-gray-500">Shipped : </span>{formatDate(data.dateShipped)}
        </div>
        <div className="p-1 border-r border-gray-200 border-t border-gray-200">
          <span className="text-gray-500">Ordered By : </span>{data.orderedBy}
        </div>
        <div className="p-1 border-t border-gray-200">
          <span className="text-gray-500">Packed By : </span>{data.packedBy}
        </div>
        <div className="p-1 border-r border-gray-200 border-t border-gray-200">
          <span className="text-gray-500">Sales ID : </span>{data.salesId}
        </div>
        <div className="p-1 border-r border-gray-200 border-t border-gray-200">
          <span className="text-gray-500">Terms : </span>{data.terms}
        </div>
        <div className="p-1 border-t border-gray-200" colSpan={2}>
          <span className="text-gray-500">FOB : </span>{data.fob}
        </div>
      </div>

      {/* Line Items */}
      <table className="w-full text-[9px] border-collapse mb-3">
        <thead>
          <tr className="border-b-2 border-gray-400">
            <th className="text-left py-1 px-1 w-20 font-bold">ItemNum</th>
            <th className="text-left py-1 px-1 font-bold">Description</th>
            <th className="text-right py-1 px-1 w-14 font-bold">QtyShip</th>
            <th className="text-right py-1 px-1 w-10 font-bold">Disc</th>
            <th className="text-right py-1 px-1 w-16 font-bold">Unit</th>
            <th className="text-right py-1 px-1 w-18 font-bold">Extended</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((ln, i) => (
            <tr key={i} className="border-b border-gray-200 avoid-break">
              <td className="py-1 px-1">{ln.itemNum}</td>
              <td className="py-1 px-1">{ln.description}</td>
              <td className="py-1 px-1 text-right">{ln.qtyShipped}</td>
              <td className="py-1 px-1 text-right">{ln.discountPct || 0}</td>
              <td className="py-1 px-1 text-right">{formatCurrency(ln.unitPrice)}</td>
              <td className="py-1 px-1 text-right">{formatCurrency(ln.extendedPrice)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Comments + Totals */}
      <div className="flex gap-4 mb-3">
        <div className="flex-1 text-[9px]">
          <div className="font-semibold mb-1">Thank you for your business.</div>
          {data.comment && (
            <>
              <div className="font-semibold text-gray-600 mb-1">Comments</div>
              <div className="whitespace-pre-wrap border border-gray-200 p-2">{data.comment}</div>
            </>
          )}
        </div>
        <div className="w-56 text-[10px]">
          <table className="w-full border-collapse">
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="py-1 font-semibold">Sales Amount</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.subtotal)}</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="py-1 font-semibold">Sales Tax</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.tax ?? 0)}</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="py-1 font-semibold">Shipping/Handling*</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.shipping ?? 0)}</td>
              </tr>
              <tr className="border-b border-gray-200 font-bold">
                <td className="py-1">Invoice Total</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.total)}</td>
              </tr>
              {data.downPayment !== undefined && (
                <tr className="border-b border-gray-200">
                  <td className="py-1 font-semibold">DownPayment</td>
                  <td className="py-1 text-right">{formatCurrency(data.downPayment)}</td>
                </tr>
              )}
              <tr className="font-bold">
                <td className="py-1">Balance Due</td>
                <td className="py-1 text-right">{formatCurrency(data.totals?.balance)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Contract Detail */}
      {data.contractDetail && (
        <div className="text-[8px] border-t border-gray-400 pt-2 mb-2">
          <div className="font-semibold mb-1">Contract Detail:</div>
          <div className="whitespace-pre-wrap text-gray-700">{data.contractDetail}</div>
        </div>
      )}

      {/* Tax disclaimer */}
      <div className="text-center text-[8px] text-gray-500 italic mt-2">
        Taxes will be calculated in $ regarding transport and other taxable services.
      </div>
    </div>
  );
}
