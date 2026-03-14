// Helper: map user JSON to OrderPrintData and OrderLineData
export function mapJsonToOrderPrintData(json: any): {
  data: OrderPrintData;
  lines: OrderLineData[];
} {
  const data: OrderPrintData = {
    id: json.id,
    ida: json.ida,
    orderNum: json.ida,
    status: json.status,
    company: json.refs?.links?.customer?.company,
    attention: json.refs?.links?.customer?.attention,
    address1: json.refs?.links?.customer?.address_full,
    phone: json.refs?.links?.customer?.phone,
    email: json.refs?.links?.customer?.email,
    customerID: json.customer_id,
    dateCreated: json.dt_created
      ? new Date(json.dt_created).toISOString().split("T")[0]
      : undefined,
    dateOrdered: json.dt_created
      ? new Date(json.dt_created).toISOString().split("T")[0]
      : undefined,
    dateShipped: undefined,
    terms: json.terms,
    total: json.totals?.total,
    amount: json.totals?.subtotal,
    salesTax: json.totals?.tax,
    shipTotal: json.totals?.shipping,
    balanceDueEstimated: json.totals?.balance,
    comment: json.comments?.public,
    contractDetail: json.conditions_description,
    pvTermState: undefined,
    contractDetailTag: undefined,
    lines: undefined,
  };

  const lines: OrderLineData[] = (json.lines || []).map(
    (line: any, idx: number) => ({
      id: line.id,
      lineNum: line.line_number ?? idx + 1,
      itemNum: line.item?.ida_item,
      description: line.item?.description,
      qtyOrdered: line.quantity?.staged ?? 0,
      qtyShipped: line.quantity?.active ?? 0,
      unitPrice: line.price?.unit,
      discount: line.price?.discount_amount,
      discountedPrice: line.price?.unit,
      extendedPrice: line.price?.extended,
    }),
  );

  return { data, lines };
}
// Example usage: show user JSON in OrderPrintDocument
// import { mapJsonToOrderPrintData } from './OrderPrintDocument';
// const { data, lines } = mapJsonToOrderPrintData(userJson);
// <OrderPrintDocument data={data} lines={lines} />
/**
 * OrderPrintDocument - Print-ready sales order document
 * US Letter (8.5" x 11") format
 */
import React from "react";
import "./legacy-invoice-print.css";
import PrintDocumentLayout from "./PrintDocumentLayout";
import { useDefaultCompany } from "@/hooks/useDefaultCompany";
import type {
  PrintDocumentMeta,
  PrintParty,
  PrintLineItem,
  PrintTotals,
  PrintComments,
  PaperSize,
} from "./printTypes";

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
  dateShipped?: string;
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
  packedBy?: string;

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

// Dummy data for legacy print preview (for visual testing)
const dummyData = {
  id: 1,
  orderNum: "INV-1001",
  company: "Advanced Chimney Techniques, Inc",
  attention: "John Doe",
  address1: "365 W Row",
  address2: "",
  city: "Jamestown",
  state: "MO",
  zip: "65046",
  country: "USA",
  phone: "660-849-2525",
  phoneCell: "555-123-4567",
  dateCreated: "2026-02-22",
  custPONum: "PO-12345",
  customerID: "CUST-001",
  typeSale: "Retail",
  dateInvoiced: "2026-02-22",
  dateShipped: "2026-02-23",
  orderedBy: "Jane Smith",
  packedBy: "Mike Brown",
  salesNameId: "S-001",
  terms: "Net 30",
  fob: "Jamestown",
  amount: 1000,
  salesTax: 80,
  shipTotal: 50,
  total: 1130,
  balanceDueEstimated: 1130,
  comment: "Thank you for your business.",
  contractDetail: "Standard contract applies.",
  pvTermState: "MO",
  contractDetailTag: "Standard",
  lines: [
    {
      itemNum: "A100",
      description: "Chimney Cap",
      qtyOrdered: 2,
      qtyShipped: 2,
      unitPrice: 400,
      discount: 0,
      discountedPrice: 400,
      extendedPrice: 800,
    },
    {
      itemNum: "B200",
      description: "Flue Liner",
      qtyOrdered: 1,
      qtyShipped: 1,
      unitPrice: 200,
      discount: 0,
      discountedPrice: 200,
      extendedPrice: 200,
    },
  ],
};

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
    documentType: "order",
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
    phoneCell: data.shipPhone,
  };

  const printLines: PrintLineItem[] = (lines || data.lines || []).map(
    (line, idx) => ({
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
    }),
  );

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
  paperSize = "letter",
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  const { meta, billTo, shipTo, printLines, totals, comments } =
    transformOrderData(data, lines);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn("OrderPrintDocument: Company data unavailable:", error);
  }

  return (
    <PrintDocumentLayout
      templateName="OrderPrintDocument.tsx"
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

export default OrderPrintDocument;
