/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Print Document Types
 * Shared types for print-ready document components
 */
import type { CompanyInfo } from '@/hooks/useDefaultCompany';
import { formatDt } from '@/utils/fieldFormatters';
import { formatCurrency as _fc } from '@/utils/stringUtils';
/** Print documents show $0.00 for missing values, not blank */
export const formatCurrency = (n: number | string | null | undefined): string =>
  _fc(n) || '$0.00';

// Paper size definitions (US Letter is 8.5" x 11")
export type PaperSize = 'letter' | 'a4';

export const PAPER_DIMENSIONS = {
  letter: { width: '8.5in', height: '11in', widthMm: 215.9, heightMm: 279.4 },
  a4: { width: '210mm', height: '297mm', widthMm: 210, heightMm: 297 },
} as const;

// Common party/address block used in bill-to, ship-to, etc.
export interface PrintParty {
  name?: string;
  company?: string;
  attention?: string;
  firstName?: string;
  lastName?: string;
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  phone?: string;
  phoneCell?: string;
  email?: string;
}

// Serial number for printing
export interface PrintSerial {
  serialIda: string;
  modelIda?: string;
  status?: string;
  warranty?: string;
  cost?: number;
}

// Line item for printing
export interface PrintLineItem {
  lineNum?: number;
  itemNum?: string;
  description?: string;
  qty?: number;
  qtyOrdered?: number;
  qtyShipped?: number;
  unitPrice?: number;
  msrp?: number;
  discount?: number;
  discountPct?: number;
  discountedPrice?: number;
  extendedPrice?: number;
  taxable?: boolean;
  notes?: string;
  serials?: PrintSerial[];
  isSerialized?: boolean;
}

// Totals block
export interface PrintTotals {
  subtotal?: number;
  salesAmount?: number;
  discount?: number;
  discountPct?: number;
  salesTax?: number;
  taxRate?: number;
  shipping?: number;
  handling?: number;
  total?: number;
  downPayment?: number;
  balanceDue?: number;
  amountPaid?: number;
}

// Document metadata
export interface PrintDocumentMeta {
  documentType:
    | 'proposal'
    | 'order'
    | 'invoice'
    | 'purchase'
    | 'workorder'
    | 'receipt'
    | 'adjustment'
    | 'requisition'
    | 'project'
    | 'creditmemo';
  documentNumber: string;
  documentDate?: string;
  dueDate?: string;
  status?: string;
  customerPO?: string;
  customerId?: string | number;
  salesId?: string;
  terms?: string;
  fob?: string;
  shipVia?: string;
  typeSale?: string;
  taxJuris?: string;
  contractDetailTag?: string;
  orderedBy?: string;
  requestedBy?: string;
  packedBy?: string;
  actionBy?: string;
  dateNeeded?: string;
  dateOrdered?: string;
  dateShipped?: string;
  dateInvoiced?: string;
}

// Comments/notes structure
export interface PrintComments {
  public?: string;
  process?: string;
  contractDetail?: string;
  pvTermState?: string;
  shipInstruct?: string;
}

// Props for base print document
export interface PrintDocumentProps {
  company: CompanyInfo | null;
  meta: PrintDocumentMeta;
  billTo?: PrintParty;
  shipTo?: PrintParty;
  shipFrom?: PrintParty;
  lines: PrintLineItem[];
  totals: PrintTotals;
  comments?: PrintComments;
  showPrices?: boolean;
  showSignature?: boolean;
  paperSize?: PaperSize;
  logoUrl?: string;
}


// Date formatter utility
export const formatDate = (dateStr: string | undefined | null): string => {
  if (!dateStr) return '';
  return formatDt(dateStr, 'date');
};

// Document type labels
export const DOCUMENT_TYPE_LABELS: Record<PrintDocumentMeta['documentType'], string> = {
  proposal: 'Proposal',
  order: 'Order',
  invoice: 'Invoice',
  purchase: 'Purchase Order',
  workorder: 'Work Order',
  receipt: 'Receipt',
  adjustment: 'Adjustment',
  requisition: 'Requisition',
  project: 'Project',
  creditmemo: 'Credit Memo',
};

// Print-specific CSS classes (for @media print)
export const PRINT_STYLES = `
@media print {
  @page {
    size: letter;
    margin: 0.5in;
  }
  
  body {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  
  .print-document {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
  }
  
  .no-print {
    display: none !important;
  }
  
  .page-break {
    page-break-before: always;
  }
  
  .avoid-break {
    page-break-inside: avoid;
  }
  
  table {
    page-break-inside: auto;
  }
  
  tr {
    page-break-inside: avoid;
    page-break-after: auto;
  }
  
  thead {
    display: table-header-group;
  }
  
  tfoot {
    display: table-footer-group;
  }
}
`;
