/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PrintDocumentLayout - Base layout for print-ready documents
 * US Letter size (8.5" x 11") optimized
 */
import React from 'react';
import type { 
  PrintDocumentProps, 
  PrintParty,
  PrintLineItem,
} from './printTypes';
import { 
  formatCurrency, 
  formatDate,
  DOCUMENT_TYPE_LABELS,
  PAPER_DIMENSIONS,
} from './printTypes';

// Render a party block as a card — title header, label-above-value fields
const PartyBlock: React.FC<{ title: string; party?: PrintParty }> = ({ title, party }) => {
  if (!party) return null;

  const fullName = [party.firstName, party.lastName].filter(Boolean).join(' ') || party.name;
  const cityStateZip = [
    [party.city, party.state].filter(Boolean).join(', '),
    party.zip,
  ].filter(Boolean).join(' ');
  const country = party.country && party.country !== 'US' && party.country !== 'USA' ? party.country : '';

  // Collect non-empty fields as label/value pairs
  const fields: { label: string; value: string }[] = [];
  if (party.attention) fields.push({ label: 'Attn', value: party.attention });
  if (fullName) fields.push({ label: 'Name', value: fullName });
  if (party.company) fields.push({ label: 'Company', value: party.company });
  const addrLines = [party.address1, party.address2].filter(Boolean).join(', ');
  if (addrLines) fields.push({ label: 'Address', value: addrLines });
  if (cityStateZip) fields.push({ label: 'City/State', value: cityStateZip + (country ? ` ${country}` : '') });
  if (party.phone) fields.push({ label: 'Phone', value: party.phone });
  if (party.email) fields.push({ label: 'Email', value: party.email });

  return (
    <div className="border border-gray-200 rounded">
      <div className="bg-gray-50 px-2 py-1 border-b border-gray-200">
        <span className="text-[9px] text-gray-500 uppercase tracking-wider font-medium">{title}</span>
      </div>
      <div className="grid grid-cols-2 gap-0">
        {fields.map((f, i) => (
          <div key={i} className="px-2 py-1 border-b border-gray-100 last:border-b-0">
            <div className="text-[9px] text-gray-400 uppercase tracking-wider leading-tight">{f.label}</div>
            <div className="text-[11px] text-gray-800 leading-tight mt-0.5">{f.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Detail card — label on top, value below, controlled spacing
const DetailCard: React.FC<{ label: string; value?: string | number | null }> = ({ label, value }) => {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="px-2 py-1">
      <div className="text-[9px] text-gray-400 uppercase tracking-wider leading-tight">{label}</div>
      <div className="text-[11px] text-gray-800 leading-tight mt-0.5">{value}</div>
    </div>
  );
};

// Line items table
const LinesTable: React.FC<{ 
  lines: PrintLineItem[]; 
  showPrices?: boolean;
  documentType: string;
}> = ({ lines, showPrices = true, documentType }) => {
  const isInvoice = documentType === 'invoice' || documentType === 'creditmemo';
  const isPurchase = documentType === 'purchase';
  
  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="border-b border-gray-300 bg-gray-50">
          <th className="text-left py-1 px-1 w-16">Qty</th>
          <th className="text-left py-1 px-1 w-24">Item #</th>
          <th className="text-left py-1 px-1">Description</th>
          {showPrices && (
            <>
              {!isPurchase && <th className="text-right py-1 px-1 w-16">MSRP</th>}
              <th className="text-right py-1 px-1 w-16">Unit</th>
              <th className="text-right py-1 px-1 w-20">Extended</th>
            </>
          )}
        </tr>
      </thead>
      <tbody>
        {lines.map((line, idx) => (
          <tr key={idx} className="border-b border-gray-200 avoid-break">
            <td className="py-1 px-1 text-right">
              {isInvoice ? line.qtyShipped : line.qtyOrdered || line.qty}
            </td>
            <td className="py-1 px-1">{line.itemNum}</td>
            <td className="py-1 px-1">{line.description}</td>
            {showPrices && (
              <>
                {!isPurchase && (
                  <td className="py-1 px-1 text-right">{formatCurrency(line.msrp || line.unitPrice)}</td>
                )}
                <td className="py-1 px-1 text-right">{formatCurrency(line.discountedPrice || line.unitPrice)}</td>
                <td className="py-1 px-1 text-right">{formatCurrency(line.extendedPrice)}</td>
              </>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export interface PrintDocumentLayoutProps extends PrintDocumentProps {
  templateName?: string;
  partyTitles?: {
    billTo?: string;
    shipTo?: string;
    shipFrom?: string;
  };
  children?: React.ReactNode;
}

const PrintDocumentLayout: React.FC<PrintDocumentLayoutProps> = ({
  company,
  meta,
  billTo,
  shipTo,
  shipFrom,
  lines,
  totals,
  comments,
  showPrices = true,
  showSignature = true,
  paperSize = 'letter',
  logoUrl,
  templateName,
  partyTitles,
  children,
}) => {
  const dimensions = PAPER_DIMENSIONS[paperSize];
  const typeLabel = DOCUMENT_TYPE_LABELS[meta.documentType];
  const resolvedLogoUrl = logoUrl || company?.logoUrl || '/images/logo/webclerk.png';
  const primeParty: PrintParty = {
    attention: company?.attention,
    company: company?.name,
    address1: (company as any)?.address_full || company?.address?.line1,
    address2:
      company?.address?.line2 ||
      (company?.domain ? `Domain: ${company.domain}` : undefined),
    city: company?.address?.city,
    state: company?.address?.state,
    zip: company?.address?.zip,
    country: company?.address?.country,
    phone: (company as any)?.phone || company?.phone,
    email: (company as any)?.email || company?.email,
  };
  const markerFlag = (import.meta.env.VITE_PRINT_TEMPLATE_MARKER || '').toLowerCase();
  const showTemplateMarker = markerFlag
    ? ['1', 'true', 'yes', 'on'].includes(markerFlag)
    : import.meta.env.DEV;

  return (
    <div
      className="print-document bg-white text-black font-sans"
      style={{
        width: dimensions.width,
        minHeight: dimensions.height,
        padding: '0.5in',
        boxSizing: 'border-box',
      }}
    >
      {/* Dev marker: helps identify which print template rendered this document */}
      {showTemplateMarker && (
        <div className="flex justify-end mb-2">
          <span className="text-[10px] uppercase tracking-wide text-gray-600 border border-dashed border-gray-400 px-2 py-0.5 rounded-sm">
            Template: {templateName || `${meta.documentType}PrintTemplate`}
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-start mb-4 pb-2 border-b border-gray-300">
        {/* Logo + Company Info - Left */}
        <div className="text-xs w-1/3">
          <div className="mb-2">
            <img
              src={resolvedLogoUrl}
              alt={company?.name || 'WebClerk Logo'}
              className="max-h-16 max-w-full object-contain"
            />
          </div>
          {company?.website && (
            <p>
              <a href={company.website} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
                {company.website.replace('https://', '').replace('http://', '')}
              </a>
            </p>
          )}
        </div>
        
        {/* Center Spacer */}
        <div className="w-1/3" />
        
        {/* Document Info - Right */}
        <div className="text-right w-1/3">
          <p className="text-sm">{company?.name}</p>
          <h2 className="text-xl font-bold mt-1">
            {typeLabel}: {meta.documentNumber}
          </h2>
          {meta.documentDate && (
            <p className="text-xs text-gray-600 mt-1">
              Date: {formatDate(meta.documentDate)}
            </p>
          )}
        </div>
      </div>

      {/* Party Addresses Row */}
      <div className="grid grid-cols-3 gap-4 mb-2">
        <PartyBlock title="Prime Company" party={primeParty} />
        <PartyBlock title={partyTitles?.billTo || 'Bill To'} party={billTo} />
        <PartyBlock title={partyTitles?.shipTo || 'Ship To'} party={shipTo} />
      </div>

      {shipFrom && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <PartyBlock title={partyTitles?.shipFrom || 'Ship From'} party={shipFrom} />
        </div>
      )}

      {/* Contract Detail Tag (Large centered text) */}
      {meta.contractDetailTag && (
        <div className="text-center text-3xl font-bold text-gray-800 my-4">
          {meta.contractDetailTag}
        </div>
      )}

      {/* Detail Cards — grouped by function, label above value */}
      <div className="border border-gray-200 rounded mb-4">
        <div className="grid grid-cols-4 divide-x divide-gray-200 border-b border-gray-200">
          <DetailCard label={typeLabel + " #"} value={meta.documentNumber} />
          <DetailCard label="Account" value={meta.customerId} />
          <DetailCard label="Cust PO#" value={meta.customerPO} />
          <DetailCard label="Date" value={formatDate(meta.documentDate)} />
        </div>
        <div className="grid grid-cols-4 divide-x divide-gray-200">
          <DetailCard label="Terms" value={meta.terms} />
          <DetailCard label={meta.documentType === 'proposal' ? 'Requested By' : 'Ordered By'}
                     value={meta.requestedBy || meta.orderedBy} />
          <DetailCard label="Sales ID" value={meta.salesId} />
          <DetailCard label={meta.documentType === 'invoice' || meta.documentType === 'creditmemo' ? 'Invoice Date' : 'Date Needed'}
                     value={formatDate(meta.dateNeeded || meta.dateInvoiced)} />
        </div>
        {(meta.shipVia || meta.fob || meta.typeSale || meta.taxJuris || meta.actionBy || meta.packedBy) && (
          <div className="grid grid-cols-4 divide-x divide-gray-200 border-t border-gray-200">
            <DetailCard label="Ship Via" value={meta.shipVia} />
            <DetailCard label="FOB" value={meta.fob} />
            <DetailCard label="Type Sale" value={meta.typeSale} />
            {(meta.documentType === 'invoice' || meta.documentType === 'creditmemo')
              ? <DetailCard label="Packed By" value={meta.packedBy} />
              : <DetailCard label="Tax Juris" value={meta.taxJuris} />
            }
          </div>
        )}
      </div>

      {/* Comments */}
      {comments?.public && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-gray-600 mb-1">Comments</h4>
          <p className="text-xs text-gray-700">{comments.public}</p>
        </div>
      )}

      {/* Line Items Table */}
      <div className="mb-4 border-t border-gray-300 pt-2">
        <LinesTable lines={lines} showPrices={showPrices} documentType={meta.documentType} />
      </div>

      {/* Totals and Footer */}
      <div className="flex gap-6 mb-6">
        {/* Thank you / Terms */}
        <div className="flex-1 text-xs">
          <h4 className="font-semibold text-gray-700 mb-2">Thank you for your business.</h4>
          {comments?.pvTermState && (
            <p className="text-gray-600 mt-2">{comments.pvTermState}</p>
          )}
        </div>
        
        {/* Totals Table */}
        {showPrices && (
          <div className="w-64 border-l border-gray-300 pl-4">
            <table className="w-full text-xs">
              <tbody>
                <tr>
                  <td className="py-0.5 text-gray-600">Sales Amount</td>
                  <td className="py-0.5 text-right">{formatCurrency(totals.salesAmount || totals.subtotal)}</td>
                </tr>
                <tr>
                  <td className="py-0.5 text-gray-600">Sales Tax</td>
                  <td className="py-0.5 text-right">{formatCurrency(totals.salesTax)}</td>
                </tr>
                <tr>
                  <td className="py-0.5 text-gray-600">Shipping/Handling</td>
                  <td className="py-0.5 text-right">{formatCurrency((totals.shipping || 0) + (totals.handling || 0))}</td>
                </tr>
                <tr className="border-t border-gray-400 font-semibold">
                  <td className="py-1">{typeLabel} Total</td>
                  <td className="py-1 text-right">{formatCurrency(totals.total)}</td>
                </tr>
                {totals.downPayment !== undefined && totals.downPayment > 0 && (
                  <tr>
                    <td className="py-0.5 text-gray-600">Down Payment</td>
                    <td className="py-0.5 text-right">{formatCurrency(totals.downPayment)}</td>
                  </tr>
                )}
                {totals.balanceDue !== undefined && (
                  <tr className="font-semibold">
                    <td className="py-0.5">Balance Due</td>
                    <td className="py-0.5 text-right">{formatCurrency(totals.balanceDue)}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Contract Detail */}
      {comments?.contractDetail && (
        <div className="mb-4 border-t border-gray-300 pt-2">
          <h4 className="text-xs font-medium text-gray-600 mb-1">Contract Detail</h4>
          <p className="text-xs text-gray-700 whitespace-pre-wrap">{comments.contractDetail}</p>
        </div>
      )}

      {/* Signature Block */}
      {showSignature && (meta.documentType === 'proposal' || meta.documentType === 'order' || meta.documentType === 'workorder' || meta.documentType === 'adjustment') && (
        <div className="flex gap-6 mt-6 pt-4 border-t border-gray-300">
          <div className="flex-1 text-xs">
            <div className="border border-gray-300 p-3 bg-gray-50">
              <p className="text-gray-700">
                Acceptance of the {typeLabel}: The above prices, specifications, and conditions 
                are satisfactory and are hereby accepted. {company?.name} is authorized to do 
                the work as specified. Payment will be made according to your terms.
              </p>
            </div>
          </div>
          <div className="w-72 text-xs">
            <div className="border-b border-gray-400 pb-4 mb-2">
              <span className="text-gray-600">Signature:</span>
            </div>
            <div className="flex gap-4">
              <div className="flex-1 border-b border-gray-400 pb-2">
                <span className="text-gray-600">Accepted:</span>
              </div>
              <div className="w-24 border-b border-gray-400 pb-2">
                <span className="text-gray-600">Date:</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer with reference numbers */}
      <div className="flex justify-between mt-6 pt-2 border-t border-gray-200 text-xs text-gray-600">
        <span>{typeLabel}# {meta.documentNumber}</span>
        <span>Customer# {meta.customerId}</span>
        <span className="flex items-center gap-1">
          Your PO#: <span className="border-b border-gray-400 w-24 inline-block">&nbsp;</span>
        </span>
      </div>

      {/* Custom children content */}
      {children}
    </div>
  );
};

export default PrintDocumentLayout;
