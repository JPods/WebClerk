/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * RequisitionPrintDocument - Print-ready requisition document
 */
import React from 'react';
import PrintDocumentLayout from './PrintDocumentLayout';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import type {
  PaperSize,
  PrintDocumentMeta,
  PrintParty,
  PrintLineItem,
  PrintTotals,
  PrintComments,
} from './printTypes';

export interface RequisitionPrintData {
  id: number;
  ida?: string;
  requisition_no?: string;
  status?: string;
  requested_by?: string;
  department?: string;
  priority?: string;
  notes?: string;
  dt_created?: string;
  due_date?: string;
  customer_id?: number;
  refs?: any;
  comments?: any;
}

export interface RequisitionPrintDocumentProps {
  data: RequisitionPrintData;
  paperSize?: PaperSize;
  logoUrl?: string;
}

const toCommentString = (value: unknown): string | undefined => {
  if (!value) return undefined;
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    return value
      .map((entry: any) => (typeof entry === 'string' ? entry : entry?.mgs))
      .filter(Boolean)
      .join('\n');
  }
  return String(value);
};

const transformRequisitionData = (data: RequisitionPrintData) => {
  const customer = Array.isArray(data.refs?.links?.customer)
    ? data.refs?.links?.customer?.[0]
    : data.refs?.links?.customer;

  const requestor = Array.isArray(data.refs?.links?.contact)
    ? data.refs?.links?.contact?.find((c: any) => c?.purpose === 'billto')
    : undefined;

  const meta: PrintDocumentMeta = {
    documentType: 'requisition',
    documentNumber: data.requisition_no || data.ida || String(data.id),
    documentDate: data.dt_created,
    dateNeeded: data.due_date,
    status: data.status,
    customerId: data.customer_id,
    requestedBy: data.requested_by,
    actionBy: data.department,
    typeSale: data.priority,
  };

  const billTo: PrintParty = {
    attention: requestor?.display_name,
    firstName: requestor?.name_first,
    lastName: requestor?.name_last,
    company: customer?.company || customer?.display_name,
    address1: customer?.address_full,
    phone: requestor?.phone || customer?.phone,
    email: requestor?.email || customer?.email,
  };

  const lines: PrintLineItem[] = [];

  const totals: PrintTotals = {
    subtotal: 0,
    salesTax: 0,
    shipping: 0,
    total: 0,
  };

  const comments: PrintComments = {
    public: toCommentString(data.comments?.public) || data.notes,
    process: data.department,
  };

  return { meta, billTo, lines, totals, comments };
};

const RequisitionPrintDocument: React.FC<RequisitionPrintDocumentProps> = ({
  data,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  const { meta, billTo, lines, totals, comments } = transformRequisitionData(data);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('RequisitionPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="RequisitionPrintDocument.tsx"
      company={company}
      meta={meta}
      billTo={billTo}
      lines={lines}
      totals={totals}
      comments={comments}
      showPrices={false}
      showSignature={false}
      paperSize={paperSize}
      logoUrl={logoUrl}
    >
      <div className="mt-4 p-3 border border-slate-300 rounded text-xs">
        <h4 className="font-semibold mb-1">Requisition Notes</h4>
        <p className="text-slate-700 whitespace-pre-wrap">{data.notes || 'No notes provided.'}</p>
      </div>
    </PrintDocumentLayout>
  );
};

export default RequisitionPrintDocument;
