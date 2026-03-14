/**
 * WorkorderPrintDocument - Print-ready work order document
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

// Props interface for raw work order data (from API)
export interface WorkorderPrintData {
  id: number;
  ida?: string;
  workorderNum?: string;
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
  dateStarted?: string;
  dateCompleted?: string;
  dateNeeded?: string;
  custPONum?: string;
  technicianId?: string;
  priority?: string;
  terms?: string;
  fob?: string;
  workDescription?: string;

  // Financials
  amount?: number;
  laborCost?: number;
  materialCost?: number;
  salesTax?: number;
  total?: number;

  // Comments
  comment?: string;
  contractDetail?: string;
  pvTermState?: string;

  // Lines
  lines?: WorkorderLineData[];
}

export interface WorkorderLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  description?: string;
  qty?: number;
  unitPrice?: number;
  laborHours?: number;
  laborRate?: number;
  extendedPrice?: number;
}

export interface WorkorderPrintDocumentProps {
  data: WorkorderPrintData;
  lines?: WorkorderLineData[];
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw work order data to print format
const transformWorkorderData = (data: WorkorderPrintData, lines?: WorkorderLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'workorder',
    documentNumber: data.workorderNum || data.ida || String(data.id),
    documentDate: data.dateCreated,
    status: data.status,
    customerPO: data.custPONum,
    customerId: data.customerID,
    salesId: data.technicianId,
    terms: data.terms,
    fob: data.fob,
    dateOrdered: data.dateStarted,
    dateNeeded: data.dateCompleted,
    actionBy: data.priority,
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

  // Ship-to can be same as bill-to for work orders
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
    qty: line.qty,
    unitPrice: line.unitPrice,
    extendedPrice: line.extendedPrice,
  }));

  const totals: PrintTotals = {
    salesAmount: data.amount,
    subtotal: data.laborCost,
    shipping: data.materialCost,
    salesTax: data.salesTax,
    total: data.total,
  };

  const comments: PrintComments = {
    public: data.comment,
    process: data.workDescription,
    contractDetail: data.contractDetail,
    pvTermState: data.pvTermState,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const WorkorderPrintDocument: React.FC<WorkorderPrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  showSignature = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();

  const { meta, billTo, shipTo, printLines, totals, comments } = transformWorkorderData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('WorkorderPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="WorkorderPrintDocument.tsx"
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

export default WorkorderPrintDocument;