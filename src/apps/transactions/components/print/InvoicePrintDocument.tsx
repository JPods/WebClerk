/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * InvoicePrintDocument - Print-ready invoice document
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

// Props interface for raw invoice data (from API)
export interface InvoicePrintData {
  id: number;
  ida?: string;
  invoiceNum?: string;
  orderNum?: string;
  status?: string;
  
  // Customer/Party info
  customerID?: number | string;
  firstName?: string;
  lastName?: string;
  company?: string;
  attention?: string;
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  phone?: string;
  phoneCell?: string;
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
  dateInvoiced?: string;
  dateShipped?: string;
  dateDue?: string;
  custPONum?: string;
  salesNameId?: string;
  terms?: string;
  fob?: string;
  shipVia?: string;
  typeSale?: string;
  taxJuris?: string;
  orderedBy?: string;
  packedBy?: string;
  contractDetailTag?: string;
  
  // Financials — JSON envelope is source of truth
  totals?: Record<string, number>;
  downPayment?: number;
  invoices_BalanceDue?: number;
  
  // Comments
  comment?: string;
  contractDetail?: string;
  pvTermState?: string;
  shipInstruct?: string;
  
  // Lines
  lines?: InvoiceLineData[];
}

export interface InvoiceLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  description?: string;
  qty?: number;
  qtyShipped?: number;
  unitPrice?: number;
  msrp?: number;
  discount?: number;
  discountedPrice?: number;
  extendedPrice?: number;
}

export interface InvoicePrintDocumentProps {
  data: InvoicePrintData;
  lines?: InvoiceLineData[];
  showPrices?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw invoice data to print format
const transformInvoiceData = (data: InvoicePrintData, lines?: InvoiceLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'invoice',
    documentNumber: data.invoiceNum || data.ida || String(data.id),
    documentDate: data.dateInvoiced || data.dateCreated,
    dueDate: data.dateDue,
    status: data.status,
    customerPO: data.custPONum,
    customerId: data.customerID,
    salesId: data.salesNameId,
    terms: data.terms,
    fob: data.fob,
    shipVia: data.shipVia,
    typeSale: data.typeSale,
    taxJuris: data.taxJuris,
    dateInvoiced: data.dateInvoiced,
    dateShipped: data.dateShipped,
    orderedBy: data.orderedBy,
    packedBy: data.packedBy,
    contractDetailTag: data.contractDetailTag,
  };

  const billTo: PrintParty = {
    attention: data.attention,
    firstName: data.firstName,
    lastName: data.lastName,
    company: data.company,
    address1: data.address1,
    address2: data.address2,
    city: data.city,
    state: data.state,
    zip: data.zip,
    country: data.country,
    phone: data.phone,
    email: data.email,
  };

  const shipTo: PrintParty = {
    attention: data.shipAttention || data.attention,
    company: data.company,
    address1: data.shipAddress1 || data.address1,
    address2: data.shipAddress2 || data.address2,
    city: data.shipCity || data.city,
    state: data.shipState || data.state,
    zip: data.shipZip || data.zip,
    country: data.shipCountry || data.country,
    phone: data.shipPhone,
    email: data.shipEmail,
  };

  const printLines: PrintLineItem[] = (lines || data.lines || []).map((line, idx) => ({
    lineNum: line.lineNum || idx + 1,
    itemNum: line.itemNum,
    description: line.description,
    qty: line.qty,
    qtyShipped: line.qtyShipped || line.qty,
    unitPrice: line.unitPrice,
    msrp: line.msrp || line.unitPrice,
    discount: line.discount,
    discountedPrice: line.discountedPrice || line.unitPrice,
    extendedPrice: line.extendedPrice,
  }));

  const totals: PrintTotals = {
    salesAmount: data.totals?.subtotal,
    salesTax: data.totals?.tax,
    shipping: data.totals?.shipping,
    total: data.totals?.total,
    downPayment: data.downPayment || data.invoices_BalanceDue,
    amountPaid: data.totals?.received,
    balanceDue: data.totals?.balance,
  };

  const comments: PrintComments = {
    public: data.comment,
    contractDetail: data.contractDetail,
    pvTermState: data.pvTermState,
    shipInstruct: data.shipInstruct,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const InvoicePrintDocument: React.FC<InvoicePrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  
  const { meta, billTo, shipTo, printLines, totals, comments } = transformInvoiceData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('InvoicePrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="InvoicePrintDocument.tsx"
      partyTitles={{ billTo: 'Customer Bill To', shipTo: 'Customer Ship To' }}
      company={company}
      meta={meta}
      billTo={billTo}
      shipTo={shipTo}
      lines={printLines}
      totals={totals}
      comments={comments}
      showPrices={showPrices}
      showSignature={false} // Invoices don't typically need signature block
      paperSize={paperSize}
      logoUrl={logoUrl}
    >
      {/* Tax disclaimer */}
      <div className="text-center text-xs text-gray-500 italic mt-4">
        Taxes will be calculated regarding transport and other taxable services.
      </div>
    </PrintDocumentLayout>
  );
};

export default InvoicePrintDocument;
