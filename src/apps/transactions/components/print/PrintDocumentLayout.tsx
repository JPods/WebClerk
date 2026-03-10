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

// Render a party block (bill-to, ship-to, etc.)
const PartyBlock: React.FC<{ title: string; party?: PrintParty }> = ({ title, party }) => {
  if (!party) return null;
  
  const fullName = [party.firstName, party.lastName].filter(Boolean).join(' ') || party.name;
  
  return (
    <div className="text-xs">
      <p className="text-gray-500 mb-1 font-medium">{title}:</p>
      {party.attention && <p className="text-gray-700">{party.attention}</p>}
      {fullName && <p className="text-gray-700">{fullName}</p>}
      {party.company && <p className="text-gray-700">{party.company}</p>}
      {party.address1 && <p className="text-gray-700">{party.address1}</p>}
      {party.address2 && <p className="text-gray-700">{party.address2}</p>}
      {(party.city || party.state || party.zip) && (
        <p className="text-gray-700">
          {[party.city, party.state].filter(Boolean).join(', ')} {party.zip}
          {party.country && party.country !== 'US' && party.country !== 'USA' && ` ${party.country}`}
        </p>
      )}
      {party.phone && <p className="text-gray-700">Phone: {party.phone}</p>}
      {party.email && <p className="text-gray-700">{party.email}</p>}
    </div>
  );
};

// Detail row component
const DetailRow: React.FC<{ label: string; value?: string | number | null }> = ({ label, value }) => {
  if (value === undefined || value === null || value === '') return null;
  return (
    <>
      <span className="text-gray-500 text-[10px]">{label}:</span>
      <span className="text-gray-800 text-[10px]">{value}</span>
    </>
  );
};

// Line items table
const LinesTable: React.FC<{ 
  lines: PrintLineItem[]; 
  showPrices?: boolean;
  documentType: string;
}> = ({ lines, showPrices = true, documentType }) => {
  const isInvoice = documentType === 'invoice';
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
  children,
}) => {
  const dimensions = PAPER_DIMENSIONS[paperSize];
  const typeLabel = DOCUMENT_TYPE_LABELS[meta.documentType];
  const resolvedLogoUrl = logoUrl || company?.logoUrl || '/images/logo/webclerk.png';

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
          <p>{company?.address.line1}</p>
          {company?.address.line2 && <p>{company.address.line2}</p>}
          <p>{company?.address.city}, {company?.address.state} {company?.address.zip}</p>
          <p>{company?.phone}</p>
          <p>{company?.email}</p>
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
      <div className="grid grid-cols-4 gap-4 mb-4">
        <PartyBlock title="Bill To" party={billTo} />
        <PartyBlock title="Ship To" party={shipTo} />
        {shipFrom && <PartyBlock title="Ship From" party={shipFrom} />}
        {meta.shipVia && (
          <div className="text-xs">
            <p className="text-gray-500 mb-1 font-medium">Ship Via:</p>
            <p className="text-gray-700">{meta.shipVia}</p>
          </div>
        )}
      </div>

      {/* Contract Detail Tag (Large centered text) */}
      {meta.contractDetailTag && (
        <div className="text-center text-3xl font-bold text-gray-800 my-4">
          {meta.contractDetailTag}
        </div>
      )}

      {/* Detail Grid */}
      <div className="grid grid-cols-8 gap-x-2 gap-y-1 mb-4 text-xs border-y border-gray-200 py-2">
        <DetailRow label="Cust PO#" value={meta.customerPO} />
        <DetailRow label="Account" value={meta.customerId} />
        <DetailRow label={typeLabel + " #"} value={meta.documentNumber} />
        <DetailRow label="Type Sale" value={meta.typeSale} />
        
        <DetailRow label={meta.documentType === 'invoice' ? 'Invoice Date' : 'Date Needed'} 
                   value={formatDate(meta.dateNeeded || meta.dateInvoiced || meta.documentDate)} />
        <DetailRow label="Tax Juris" value={meta.taxJuris} />
        <DetailRow label={meta.documentType === 'proposal' ? 'Requested By' : 'Ordered By'} 
                   value={meta.requestedBy || meta.orderedBy} />
        <DetailRow label="Action By" value={meta.actionBy} />
        
        <DetailRow label="Sales ID" value={meta.salesId} />
        <DetailRow label="Terms" value={meta.terms} />
        <DetailRow label="FOB" value={meta.fob} />
        {meta.documentType === 'invoice' && <DetailRow label="Packed By" value={meta.packedBy} />}
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
