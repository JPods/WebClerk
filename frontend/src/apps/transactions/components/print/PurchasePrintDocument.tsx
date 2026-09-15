/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PurchasePrintDocument - Print-ready purchase order document
 * US Letter (8.5" x 11") format
 */
import React from 'react';
import PrintDocumentLayout from './PrintDocumentLayout';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import type { 
  PrintDocumentMeta, 
  PrintParty, 
  PrintLineItem, 
  PrintTotals,
  PrintComments,
  PaperSize,
} from './printTypes';

// Props interface for raw purchase order data (from API)
export interface PurchasePrintData {
  id: number;
  ida?: string;
  purchaseNum?: string;
  poNum?: string;
  status?: string;
  
  // Vendor info
  vendorID?: number | string;
  vendorName?: string;
  vendorCompany?: string;
  attention?: string;
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  phone?: string;
  phoneCell?: string;
  fax?: string;
  email?: string;
  
  // Shipping contact info
  shipAttention?: string;
  shipAddress1?: string;
  shipAddress2?: string;
  shipCity?: string;
  shipState?: string;
  shipZip?: string;
  shipCountry?: string;
  shipPhone?: string;
  shipEmail?: string;
  
  // Document details
  dateCreated?: string;
  dateOrdered?: string;
  dateExpected?: string;
  dateNeeded?: string;
  ourPONum?: string;
  vendorRef?: string;
  buyerId?: string;
  terms?: string;
  fob?: string;
  shipVia?: string;
  freightTerms?: string;
  
  // Ship-to (our warehouse)
  shipToName?: string;
  shipToAddress1?: string;
  shipToAddress2?: string;
  shipToCity?: string;
  shipToState?: string;
  shipToZip?: string;
  shipToCountry?: string;
  
  // Financials — JSON envelope is source of truth
  totals?: Record<string, number>;
  
  // Comments
  comment?: string;
  specialInstructions?: string;
  internalNotes?: string;
  
  // Lines
  lines?: PurchaseLineData[];
}

export interface PurchaseLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  vendorItemNum?: string;
  description?: string;
  qtyOrdered?: number;
  qtyReceived?: number;
  unitCost?: number;
  extendedCost?: number;
  dateExpected?: string;
}

export interface PurchasePrintDocumentProps {
  data: PurchasePrintData;
  lines?: PurchaseLineData[];
  showPrices?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw purchase data to print format
const transformPurchaseData = (data: PurchasePrintData, lines?: PurchaseLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'purchase',
    documentNumber: data.purchaseNum || data.poNum || data.ida || String(data.id),
    documentDate: data.dateOrdered || data.dateCreated,
    status: data.status,
    customerPO: data.ourPONum,
    customerId: data.vendorID,
    salesId: data.buyerId,
    terms: data.terms,
    fob: data.fob,
    shipVia: data.shipVia,
    dateNeeded: data.dateNeeded || data.dateExpected,
    orderedBy: data.buyerId,
  };

  // Vendor as "Bill To" equivalent
  const billTo: PrintParty = {
    name: data.vendorName,
    company: data.vendorCompany || data.vendorName,
    attention: data.attention,
    address1: data.address1,
    address2: data.address2,
    city: data.city,
    state: data.state,
    zip: data.zip,
    country: data.country,
    phone: data.phone,
    email: data.email,
  };

  // Ship-to is our receiving location
  const shipTo: PrintParty = {
    attention: data.shipAttention,
    address1: data.shipAddress1,
    address2: data.shipAddress2,
    city: data.shipCity,
    state: data.shipState,
    zip: data.shipZip,
    country: data.shipCountry,
    phone: data.shipPhone,
    email: data.shipEmail,
  };

  const printLines: PrintLineItem[] = (lines || data.lines || []).map((line, idx) => ({
    lineNum: line.lineNum || idx + 1,
    itemNum: line.vendorItemNum || line.itemNum,
    description: line.description,
    qtyOrdered: line.qtyOrdered,
    qtyShipped: line.qtyReceived,
    unitPrice: line.unitCost,
    discountedPrice: line.unitCost,
    extendedPrice: line.extendedCost,
  }));

  const totals: PrintTotals = {
    subtotal: data.totals?.subtotal,
    salesTax: data.totals?.tax,
    shipping: data.totals?.shipping,
    total: data.totals?.total,
  };

  const comments: PrintComments = {
    public: data.comment,
    process: data.internalNotes,
    shipInstruct: data.specialInstructions,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const PurchasePrintDocument: React.FC<PurchasePrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  
  const { meta, billTo, shipTo, printLines, totals, comments } = transformPurchaseData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('PurchasePrintDocument: Company data unavailable:', error);
  }

  // For PO, bill-to label should be "Vendor"
  // And ship-to should default to company address if not specified
  const effectiveShipTo: PrintParty = shipTo.address1 ? shipTo : (company ? {
    name: company.name,
    address1: company.address.line1,
    address2: company.address.line2,
    city: company.address.city,
    state: company.address.state,
    zip: company.address.zip,
    phone: company.phone,
  } : shipTo);

  return (
    <PrintDocumentLayout
      templateName="PurchasePrintDocument.tsx"
      partyTitles={{ billTo: 'Vendor', shipTo: 'Customer Ship To' }}
      company={company}
      meta={meta}
      billTo={billTo} // This is actually the Vendor
      shipTo={effectiveShipTo} // Ship to our location
      lines={printLines}
      totals={totals}
      comments={comments}
      showPrices={showPrices}
      showSignature={false}
      paperSize={paperSize}
      logoUrl={logoUrl}
    >
      {/* Special instructions */}
      {comments.shipInstruct && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs">
          <h4 className="font-semibold text-yellow-800 mb-1">Special Instructions:</h4>
          <p className="text-yellow-700">{comments.shipInstruct}</p>
        </div>
      )}
      
      {/* Vendor acknowledgment section */}
      <div className="mt-6 pt-4 border-t border-gray-300 text-xs">
        <div className="flex gap-6">
          <div className="flex-1">
            <p className="text-gray-700 mb-4">
              Please confirm this order and provide expected ship date.
            </p>
          </div>
          <div className="w-72">
            <div className="border-b border-gray-400 pb-4 mb-2">
              <span className="text-gray-600">Vendor Acknowledgment:</span>
            </div>
            <div className="flex gap-4">
              <div className="flex-1 border-b border-gray-400 pb-2">
                <span className="text-gray-600">Date:</span>
              </div>
              <div className="flex-1 border-b border-gray-400 pb-2">
                <span className="text-gray-600">Ship Date:</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PrintDocumentLayout>
  );
};

export default PurchasePrintDocument;
