/**
 * ProjectPrintDocument - Print-ready project summary document
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

export interface ProjectPrintData {
  id: number;
  ida?: string;
  name?: string;
  description?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  customer_id?: number;
  refs?: any;
  comments?: any;
}

export interface ProjectPrintDocumentProps {
  data: ProjectPrintData;
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

const transformProjectData = (data: ProjectPrintData) => {
  const customer = Array.isArray(data.refs?.links?.customer)
    ? data.refs?.links?.customer?.[0]
    : data.refs?.links?.customer;

  const meta: PrintDocumentMeta = {
    documentType: 'project',
    documentNumber: data.name || data.ida || String(data.id),
    documentDate: data.start_date,
    dueDate: data.end_date,
    status: data.status,
    customerId: data.customer_id,
    customerPO: data.ida,
  };

  const billTo: PrintParty = {
    company: customer?.company || customer?.display_name,
    attention: customer?.display_name,
    address1: customer?.address_full,
    phone: customer?.phone,
    email: customer?.email,
  };

  const lines: PrintLineItem[] = [];

  const totals: PrintTotals = {
    subtotal: 0,
    salesTax: 0,
    shipping: 0,
    total: 0,
  };

  const comments: PrintComments = {
    public: toCommentString(data.comments?.public) || data.description,
    process: toCommentString(data.comments?.process),
  };

  return { meta, billTo, lines, totals, comments };
};

const ProjectPrintDocument: React.FC<ProjectPrintDocumentProps> = ({
  data,
  paperSize = 'letter',
  logoUrl,
}) => {
  const { company, loading, error } = useDefaultCompany();
  const { meta, billTo, lines, totals, comments } = transformProjectData(data);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !company) {
    console.warn('ProjectPrintDocument: Company data unavailable:', error);
  }

  return (
    <PrintDocumentLayout
      templateName="ProjectPrintDocument.tsx"
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
      <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
        <div className="border border-slate-300 rounded p-3">
          <h4 className="font-semibold mb-1">Project Start</h4>
          <p className="text-slate-700">{data.start_date || '--'}</p>
        </div>
        <div className="border border-slate-300 rounded p-3">
          <h4 className="font-semibold mb-1">Project End</h4>
          <p className="text-slate-700">{data.end_date || '--'}</p>
        </div>
      </div>
      <div className="mt-4 p-3 border border-slate-300 rounded text-xs">
        <h4 className="font-semibold mb-1">Project Description</h4>
        <p className="text-slate-700 whitespace-pre-wrap">{data.description || 'No description provided.'}</p>
      </div>
    </PrintDocumentLayout>
  );
};

export default ProjectPrintDocument;
