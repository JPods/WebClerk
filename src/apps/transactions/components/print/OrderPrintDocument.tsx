/**
 * OrderPrintDocument - Print-ready sales order document
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

// Props interface for raw order data (from API)
export interface OrderPrintData {
  id: number;
  ida?: string;
  orderNum?: string;
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
  dateOrdered?: string;
  dateNeeded?: string;
  custPONum?: string;
  salesNameId?: string;
  terms?: string;
  fob?: string;
  shipVia?: string;
  typeSale?: string;
  taxJuris?: string;
  orderedBy?: string;
  actionBy?: string;
  contractDetailTag?: string;
  
  // Financials
  amount?: number;
  salesTax?: number;
  shipTotal?: number;
  total?: number;
  balanceDueEstimated?: number;
  
  // Comments
  comment?: string;
  contractDetail?: string;
  pvTermState?: string;
  shipInstruct?: string;
  
  // Lines
  lines?: OrderLineData[];
}

export interface OrderLineData {
  id?: number;
  lineNum?: number;
  itemNum?: string;
  description?: string;
  qtyOrdered?: number;
  qtyShipped?: number;
  unitPrice?: number;
  msrp?: number;
  discount?: number;
  discountedPrice?: number;
  extendedPrice?: number;
}

export interface OrderPrintDocumentProps {
  data: OrderPrintData;
  lines?: OrderLineData[];
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}

// Transform raw order data to print format
const transformOrderData = (data: OrderPrintData, lines?: OrderLineData[]) => {
  const meta: PrintDocumentMeta = {
    documentType: 'order',
    documentNumber: data.orderNum || data.ida || String(data.id),
    documentDate: data.dateOrdered || data.dateCreated,
    status: data.status,
    customerPO: data.custPONum,
    customerId: data.customerID,
    salesId: data.salesNameId,
    terms: data.terms,
    fob: data.fob,
    shipVia: data.shipVia,
    typeSale: data.typeSale,
    taxJuris: data.taxJuris,
    dateOrdered: data.dateOrdered,
    dateNeeded: data.dateNeeded,
    orderedBy: data.orderedBy,
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

  const shipTo: PrintParty = {
    attention: data.attention,
    company: data.company,
    address1: data.address1,
    address2: data.address2,
    city: data.city,
    state: data.state,
    zip: data.zip,
    country: data.country,
    phone: data.phone,
    phoneCell: data.phoneCell,
  };

  const printLines: PrintLineItem[] = (lines || data.lines || []).map((line, idx) => ({
    lineNum: line.lineNum || idx + 1,
    itemNum: line.itemNum,
    description: line.description,
    qtyOrdered: line.qtyOrdered,
    qtyShipped: line.qtyShipped,
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
    balanceDue: data.balanceDueEstimated,
  };

  const comments: PrintComments = {
    public: data.comment,
    contractDetail: data.contractDetail,
    pvTermState: data.pvTermState,
    shipInstruct: data.shipInstruct,
  };

  return { meta, billTo, shipTo, printLines, totals, comments };
};

const OrderPrintDocument: React.FC<OrderPrintDocumentProps> = ({
  data,
  lines,
  showPrices = true,
  showSignature = true,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  
  const { meta, billTo, shipTo, printLines, totals, comments } = transformOrderData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('OrderPrintDocument: Company data unavailable:', error);
  }

  // Ship-from is the company
  const shipFrom: PrintParty | undefined = company ? {
    company: company.name,
    address1: company.address.line1,
    address2: company.address.line2,
    city: company.address.city,
    state: company.address.state,
    zip: company.address.zip,
    phone: company.phone,
  } : undefined;

  return (
    <PrintDocumentLayout
      company={company}
      meta={meta}
      billTo={billTo}
      shipTo={shipTo}
      shipFrom={shipFrom}
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

export default OrderPrintDocument;
