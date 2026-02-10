/**
 * ProposalPrintDocument - Print-ready proposal/quote document
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

// Props interface for raw proposal data (from API)
export interface ProposalPrintData {
  id: number;
  ida?: string;
  proposalNum?: string;
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
  
  // Document details
  dateCreated?: string;
  dateNeeded?: string;
  inquiryCode?: string;
  custPONum?: string;
  salesNameId?: string;
  terms?: string;
  fob?: string;
  typeSale?: string;
  taxJuris?: string;
  requestedBy?: string;
  actionBy?: string;
  contractDetailTag?: string;
  
  // Financials
  amount?: number;
  salesTax?: number;
  shipTotal?: number;
  total?: number;
  
  // Comments
  comment?: string;
  contractDetail?: string;
  pvTermState?: string;
  
  // Lines
  lines?: ProposalLineData[];
}

export interface ProposalLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  description?: string;
  qty?: number;
  unitPrice?: number;
  msrp?: number;
  discount?: number;
  discountedPrice?: number;
  extendedPrice?: number;
}

export interface ProposalPrintDocumentProps {
  data: ProposalPrintData;
  lines?: ProposalLineData[];
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw proposal data to print format
const transformProposalData = (data: ProposalPrintData, lines?: ProposalLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'proposal',
    documentNumber: data.proposalNum || data.ida || String(data.id),
    documentDate: data.dateCreated,
    status: data.status,
    customerPO: data.custPONum || data.inquiryCode,
    customerId: data.customerID,
    salesId: data.salesNameId,
    terms: data.terms,
    fob: data.fob,
    typeSale: data.typeSale,
    taxJuris: data.taxJuris,
    dateNeeded: data.dateNeeded,
    requestedBy: data.requestedBy,
    actionBy: data.actionBy,
    contractDetailTag: data.contractDetailTag,
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

  // Ship-to can be same as bill-to or different
  const shipTo: PrintParty = {
    attention: data.attention,
    company: data.company,
    address1: data.address1,
    address2: data.address2,
    city: data.city,
    state: data.state,
    zip: data.zip,
    country: data.country,
  };

  const printLines: PrintLineItem[] = (lines || data.lines || []).map((line, idx) => ({
    lineNum: line.lineNum || idx + 1,
    itemNum: line.itemNum,
    description: line.description,
    qty: line.qty,
    qtyOrdered: line.qty,
    unitPrice: line.unitPrice,
    msrp: line.msrp || line.unitPrice,
    discount: line.discount,
    discountedPrice: line.discountedPrice || line.unitPrice,
    extendedPrice: line.extendedPrice,
  }));

  const totals: PrintTotals = {
    salesAmount: data.amount,
    salesTax: data.salesTax,
    shipping: data.shipTotal,
    total: data.total,
  };

  const comments: PrintComments = {
    public: data.comment,
    contractDetail: data.contractDetail,
    pvTermState: data.pvTermState,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const ProposalPrintDocument: React.FC<ProposalPrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  showSignature = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  
  const { meta, billTo, shipTo, printLines, totals, comments } = transformProposalData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('ProposalPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
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

export default ProposalPrintDocument;
