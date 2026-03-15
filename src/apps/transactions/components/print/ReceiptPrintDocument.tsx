/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ReceiptPrintDocument - Print-ready receipt document
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

// Props interface for raw receipt data (from API)
export interface ReceiptPrintData {
  id: number;
  ida?: string;
  receiptNum?: string;
  invoiceNum?: string;
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
  dateReceived?: string;
  paymentMethod?: string;
  checkNumber?: string;
  reference?: string;
  receivedBy?: string;

  // Financials
  amountReceived?: number;
  amountApplied?: number;
  balanceDue?: number;

  // Comments
  comment?: string;
  memo?: string;

  // Lines (applied payments)
  lines?: ReceiptLineData[];
}

export interface ReceiptLineData {
  id?: number;
  lineNum?: number;
  invoiceNum?: string;
  description?: string;
  amount?: number;
  appliedAmount?: number;
}

export interface ReceiptPrintDocumentProps {
  data: ReceiptPrintData;
  lines?: ReceiptLineData[];
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw receipt data to print format
const transformReceiptData = (data: ReceiptPrintData, lines?: ReceiptLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'receipt',
    documentNumber: data.receiptNum || data.ida || String(data.id),
    documentDate: data.dateReceived || data.dateCreated,
    status: data.status,
    customerId: data.customerID,
    paymentMethod: data.paymentMethod,
    checkNumber: data.checkNumber,
    reference: data.reference,
    receivedBy: data.receivedBy,
  };

  const billTo: PrintParty = {
    firstName: data.firstName,
    lastName: data.lastName,
    company: data.company,
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

  const shipTo: PrintParty = {
    attention: data.shipAttention,
    company: data.company,
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
    itemNum: line.invoiceNum,
    description: line.description || `Applied to Invoice ${line.invoiceNum}`,
    qty: 1,
    unitPrice: line.appliedAmount,
    extendedPrice: line.appliedAmount,
  }));

  const totals: PrintTotals = {
    amountReceived: data.amountReceived,
    amountApplied: data.amountApplied,
    balanceDue: data.balanceDue,
  };

  const comments: PrintComments = {
    public: data.comment,
    memo: data.memo,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const ReceiptPrintDocument: React.FC<ReceiptPrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  showSignature = false,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();

  const { meta, billTo, shipTo, printLines, totals, comments } = transformReceiptData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('ReceiptPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="ReceiptPrintDocument.tsx"
      partyTitles={{ billTo: 'Customer Bill To', shipTo: 'Customer Ship To' }}
      company={company}
      meta={meta}
      billTo={billTo}
      shipTo={shipTo}
      lines={printLines}
      totals={totals}
      comments={comments}
      showPrices={showPrices}
      showSignature={showSignature}
      paperSize={paperSize}
      logoUrl={logoUrl}
    />
  );
};

export default ReceiptPrintDocument;