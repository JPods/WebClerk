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
      qtyOrdered: line.quantity?.placed,
      qtyShipped: line.quantity?.actioned,
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

  // Helper for currency formatting
  const formatCurrency = (value?: number) =>
    typeof value === "number"
      ? value.toLocaleString("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 2,
        })
      : "";

  return (
    <div
      className="container-fluid print-document"
      style={{ fontSize: 12, color: "#222", background: "#fff", padding: 0 }}
    >
      {/* Breadcrumb */}
      <nav aria-label="breadcrumb" className="brdcrm_margin hidden-print">
        <ol className="breadcrumb">
          <li className="breadcrumb-item">
            <span>Home</span>
          </li>
          <li className="breadcrumb-item">
            <span>Customer Details</span>
          </li>
          <li className="breadcrumb-item">
            <span>Invoice Details</span>
          </li>
          <li className="breadcrumb-item active" aria-current="page">
            Invoice Print
          </li>
        </ol>
      </nav>

      {/* Header */}
      <div className="row invoice-header py-2 px-1" id="invoiceHeader">
        <div className="col-4 text_size">
          <p>660-849-2525</p>
          <p>omie@advancedchimneytechniques.com</p>
          <p>www.advancedchimneytechniques.com</p>
          <p>365 W Row, Jamestown, MO 65046</p>
        </div>
        <div className="col-4 text-center">
          <img
            src={logoUrl || "/img/logo.png"}
            className="img-fluid"
            alt="Logo"
            style={{ maxHeight: 60 }}
          />
        </div>
        <div className="col-4" style={{ textAlign: "center" }}>
          <p>Advanced Chimney Techniques, Inc</p>
          <h2>INVOICE: {meta.documentNumber}</h2>
        </div>
      </div>

      {/* Print Button */}
      <button
        className="btn btn-primary hidden-print"
        style={{ margin: "10px 0" }}
        onClick={() => {
          document.title = "Invoice Print";
          window.print();
        }}
      >
        <span className="glyphicon glyphicon-print" aria-hidden="true"></span>{" "}
        Print
      </button>

      {/* Bill/Ship/Contact/Customer */}
      <div className="flex row gap-6 invoice-content pt-2" id="invoiceContent">
        <div className="row w-100">
          <div className="col-6">
            <p className="almost-gray">Bill To:</p>
            <p className="gray-ish">Attention Accounts Payable</p>
            <p className="gray-ish">
              {billTo.attention}, {billTo.company}
            </p>
            <p className="gray-ish">
              {billTo.address1} {billTo.address2}
            </p>
            <p className="gray-ish">
              {billTo.city} {billTo.state} {billTo.zip} {billTo.country}
            </p>
          </div>
          <div className="col-6">
            <p className="almost-gray">Ship To:</p>
            <p className="gray-ish">{shipTo.attention}</p>
            <p>{shipTo.company}</p>
            <p className="gray-ish">
              {shipTo.address1} {shipTo.address2}
            </p>
            <p className="gray-ish">
              {shipTo.city} {shipTo.state} {shipTo.zip} {shipTo.country}
            </p>
          </div>
        </div>
      </div>
      <div className="flex row gap-2 invoice-content pt-2" id="invoiceContent">
        <div className="col-3">
          <p className="almost-gray">Contact&nbsp;us:</p>
          <p className="gray-ish">Phone:&nbsp;{company?.phone}</p>
          <p className="gray-ish">Cell:&nbsp;{company?.phoneCell}</p>
        </div>
        <div className="col-3">
          <p className="almost-gray">Customer:</p>
          <p className="gray-ish">Phone:&nbsp;{billTo.phone}</p>
          <p className="gray-ish">Cell:&nbsp;{data.phoneCell}</p>
        </div>
      </div>

      {/* Meta Rows */}
      <div className="row">
        <div className="col-1 lable_style">CustPO#:</div>
        <div className="col-2">{meta.customerPO}</div>
        <div className="col-1 lable_style">Account:</div>
        <div className="col-2">{meta.customerId}</div>
        <div className="col-1 lable_style">Order#:</div>
        <div className="col-2">{data.orderNum}</div>
        <div className="col-1 lable_style">Type Sale:</div>
        <div className="col-2">{meta.typeSale}</div>
      </div>
      <div className="row">
        <div className="col-1 lable_style">Invoice&nbsp;Date&nbsp;:</div>
        <div className="col-2">{meta.documentDate}</div>
        <div className="col-1 lable_style">Shipped&nbsp;:</div>
        <div className="col-2">{data.dateShipped}</div>
        <div className="col-1 lable_style">Ordered&nbsp;By&nbsp;:</div>
        <div className="col-2">{meta.orderedBy}</div>
        <div className="col-1 lable_style">Packed&nbsp;By&nbsp;:</div>
        <div className="col-2">{data.packedBy}</div>
      </div>
      <div className="row">
        <div className="col-1 lable_style">Sales&nbsp;ID :</div>
        <div className="col-2">{meta.salesId}</div>
        <div className="col-1 lable_style">Terms :</div>
        <div className="col-2">{meta.terms}</div>
        <div className="col-1 lable_style">FOB :</div>
        <div className="col-2">{meta.fob}</div>
        <div className="col-1 lable_style"></div>
        <div className="col-2"></div>
      </div>

      {/* Line Items Table */}
      <div className="row">
        <div
          className="col-12 pt-1"
          style={{ borderTop: "1px solid #ccc", marginTop: "2%" }}
        >
          <table className="table table-striped" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>ItemNum</th>
                <th>Description</th>
                <th>QtyShip</th>
                <th>Disc</th>
                <th>Unit</th>
                <th>Extended</th>
              </tr>
            </thead>
            <tbody>
              {printLines.map((line, idx) => (
                <tr key={line.itemNum || idx}>
                  <td>{line.itemNum}</td>
                  <td>{line.description}</td>
                  <td className="text-right">
                    {line.qtyShipped ?? line.qtyOrdered}
                  </td>
                  <td className="text-right">{line.discount}</td>
                  <td className="text-right">
                    {formatCurrency(line.discountedPrice)}
                  </td>
                  <td className="text-right">
                    {formatCurrency(line.extendedPrice)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comments and Totals */}
      <div className="row invoice_details table-responsive mx-auto d-flex">
        <div className="col-6 pt-3">
          <h4 className="gray-ish">Thank you for your business.</h4>
          <p className="pt-3 almost-gray">{comments.pvTermState}</p>
          <h4 className="gray-ish">Comments</h4>
          <p className="almost-gray">{comments.public}</p>
        </div>
        <div className="col-6 pr-4 sub-table">
          <table className="table table-borderless">
            <tbody>
              <tr>
                <td className="bold-black">Subtotal</td>
                <td className="text_size2 text-right">
                  {formatCurrency(totals.salesAmount)}
                </td>
              </tr>
              <tr>
                <td className="bold-black">Sales Tax</td>
                <td className="text_size2 text-right">
                  {formatCurrency(totals.salesTax)}
                </td>
              </tr>
              <tr>
                <td className="bold-black">Shipping</td>
                <td className="text_size2 text-right">
                  {formatCurrency(totals.shipping)}
                </td>
              </tr>
              <tr className="last-row">
                <td className="bold-black">Total</td>
                <td className="text_size2 text-right">
                  {formatCurrency(totals.total)}
                </td>
              </tr>
              <tr>
                <td className="bold-black">Balance Due</td>
                <td className="text_size2 text-right">
                  {formatCurrency(totals.balanceDue)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Contract Detail and Footer */}
      <div
        className="col-12 pt-2"
        style={{ borderTop: "1px solid #ccc", marginTop: "2%" }}
      >
        <h4 className="gray-ish">Contract Detail: {meta.contractDetailTag}</h4>
        <p className="almost-gray">{comments.contractDetail}</p>
      </div>
      <div>
        <p className="text-center almost-gray">
          <em>
            Taxes will be calculated in $ regarding transport and other taxable
            services.
          </em>
        </p>
      </div>
      <div className="row">
        <div className="col-md-6 col-6">
          <div className="box_1">
            <p>
              Acceptance of the Proposal: The above prices, specifications, and
              conditions are satisfactory and are hereby accepted. Advanced
              Chimney Techniques, Inc. is authorized to do the work as
              specified. Payment will be made according to your terms.
            </p>
          </div>
        </div>
        <div className="col-md-6 col-6">
          <div className="sign">
            Signature: <span></span>
          </div>
          <div className="sign2">
            Accepted: <span></span> Date: <span></span>
          </div>
        </div>
      </div>
      <div className="row po_sec">
        <div className="col-md-4">
          <p>Invoice# {meta.documentNumber}</p>
        </div>
        <div className="col-md-4">
          <p>Customer# {meta.customerId}</p>
        </div>
        <div className="col-md-4">
          <div className="po_style">
            Your PO#: <span></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrderPrintDocument;
