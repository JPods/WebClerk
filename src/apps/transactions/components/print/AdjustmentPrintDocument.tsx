/**
 * AdjustmentPrintDocument - Print-ready adjustment document
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

// Props interface for raw adjustment data (from API)
export interface AdjustmentPrintData {
  id: number;
  ida?: string;
  adjustmentNum?: string;
  referenceNum?: string;
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
  adjustmentType?: string;
  reason?: string;
  approvedBy?: string;

  // Financials
  adjustmentAmount?: number;
  taxAdjustment?: number;
  totalAdjustment?: number;

  // Comments
  comment?: string;
  notes?: string;

  // Lines (adjustment details)
  lines?: AdjustmentLineData[];
}

export interface AdjustmentLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  description?: string;
  originalAmount?: number;
  adjustedAmount?: number;
  difference?: number;
}

export interface AdjustmentPrintDocumentProps {
  data: AdjustmentPrintData;
  lines?: AdjustmentLineData[];
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw adjustment data to print format
const transformAdjustmentData = (data: AdjustmentPrintData, lines?: AdjustmentLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'adjustment',
    documentNumber: data.adjustmentNum || data.ida || String(data.id),
    documentDate: data.dateCreated,
    status: data.status,
    customerId: data.customerID,
    adjustmentType: data.adjustmentType,
    reason: data.reason,
    approvedBy: data.approvedBy,
    reference: data.referenceNum,
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
    itemNum: line.itemNum,
    description: line.description,
    qty: 1,
    unitPrice: line.adjustedAmount,
    extendedPrice: line.difference,
  }));

  const totals: PrintTotals = {
    adjustmentAmount: data.adjustmentAmount,
    taxAdjustment: data.taxAdjustment,
    totalAdjustment: data.totalAdjustment,
  };

  const comments: PrintComments = {
    public: data.comment,
    notes: data.notes,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const AdjustmentPrintDocument: React.FC<AdjustmentPrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  showSignature = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();

  const { meta, billTo, shipTo, printLines, totals, comments } = transformAdjustmentData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('AdjustmentPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="AdjustmentPrintDocument.tsx"
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

export default AdjustmentPrintDocument;