/**
 * generateCommercePdf — pdfme-based PDF generation for all WC3 commerce documents.
 *
 * Replaces browser window.print() and old jsPDF approach with proper client-side
 * PDF generation using @pdfme/generator.
 *
 * Supports: Invoice, Order, Proposal, Purchase Order, Work Order, Receipt,
 * Adjustment, Requisition, Project, Statement, Tax Report, Pick List, Packing Slip.
 */
import { generate } from '@pdfme/generator';
import { text, line, rectangle, image } from '@pdfme/schemas';
import type { Template } from '@pdfme/common';
import type {
  PrintDocumentMeta,
  PrintParty,
  PrintLineItem,
  PrintTotals,
  PrintComments,
} from '@/apps/transactions/components/print/printTypes';
import {
  formatCurrency,
  formatDate,
  DOCUMENT_TYPE_LABELS,
} from '@/apps/transactions/components/print/printTypes';
import type { StatementData } from '@/apps/transactions/components/print/StatementPrintDocument';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CommercePdfData {
  companyName: string;
  companyAddress?: string;
  companyPhone?: string;
  companyEmail?: string;
  companyFax?: string;
  companyWebsite?: string;
  logoUrl?: string;
  meta: PrintDocumentMeta;
  billTo?: PrintParty;
  shipTo?: PrintParty;
  shipFrom?: PrintParty;
  lines: PrintLineItem[];
  totals: PrintTotals;
  comments?: PrintComments;
  showPrices?: boolean;
  showSignature?: boolean;
  // Proposal-specific (WC2 heritage)
  daysValidFor?: number;
  daysLeadTime?: number;
  repId?: string;
}

// ---------------------------------------------------------------------------
// Constants — US Letter in mm
// ---------------------------------------------------------------------------

const PAGE_W = 215.9;
const PAGE_H = 279.4;
const MARGIN = 12.7; // 0.5in
const CONTENT_W = PAGE_W - MARGIN * 2;
const COL_W = CONTENT_W / 3;

// Font sizes (pt)
const FONT_LG = 16;
const FONT_MD = 11;
const FONT_SM = 9;
const FONT_XS = 7;

// Line heights in mm (approx)
const LH_LG = 6;
const LH_MD = 4.5;
const LH_SM = 3.5;
const LH_XS = 3;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function partyBlock(party?: PrintParty): string {
  if (!party) return '';
  const parts: string[] = [];
  if (party.attention) parts.push(party.attention);
  const fullName = [party.firstName, party.lastName].filter(Boolean).join(' ') || party.name;
  if (fullName) parts.push(fullName);
  if (party.company) parts.push(party.company);
  if (party.address1) parts.push(party.address1);
  if (party.address2) parts.push(party.address2);
  const csz = [party.city, party.state].filter(Boolean).join(', ') +
    (party.zip ? ` ${party.zip}` : '') +
    (party.country && party.country !== 'US' && party.country !== 'USA' ? ` ${party.country}` : '');
  if (csz.trim()) parts.push(csz.trim());
  if (party.phone) parts.push(`Phone: ${party.phone}`);
  if (party.email) parts.push(party.email);
  return parts.join('\n');
}

function fmtMoney(v?: number | null): string {
  return formatCurrency(v);
}

// ---------------------------------------------------------------------------
// Template + inputs builder for transaction documents
// ---------------------------------------------------------------------------

function buildTransactionTemplate(data: CommercePdfData): { template: Template; inputs: Record<string, string>[] } {
  const typeLabel = DOCUMENT_TYPE_LABELS[data.meta.documentType] || data.meta.documentType;
  const showPrices = data.showPrices !== false;

  // ---- Build schemas (field definitions) and inputs (data) ----
  const schemas: Record<string, any>[] = [];
  const inputData: Record<string, string> = {};
  let y = MARGIN;

  // --- Company name ---
  schemas.push({
    name: 'companyName',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.5,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#111111',
    alignment: 'left',
  });
  inputData['companyName'] = data.companyName || '';

  // --- Document type + number (right side) ---
  schemas.push({
    name: 'docTitle',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.5, y },
    width: CONTENT_W * 0.5,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#333333',
    alignment: 'right',
  });
  inputData['docTitle'] = `${typeLabel}: ${data.meta.documentNumber}`;

  y += LH_LG + 3;

  // --- Company detail line ---
  const companyDetail = [data.companyAddress, data.companyPhone, data.companyEmail]
    .filter(Boolean).join('  |  ');
  if (companyDetail) {
    schemas.push({
      name: 'companyDetail',
      type: 'text',
      position: { x: MARGIN, y },
      width: CONTENT_W * 0.6,
      height: LH_SM,
      fontSize: FONT_XS,
      fontColor: '#555555',
    });
    inputData['companyDetail'] = companyDetail;
  }

  // --- Document date (right) ---
  schemas.push({
    name: 'docDate',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.6, y },
    width: CONTENT_W * 0.4,
    height: LH_SM,
    fontSize: FONT_SM,
    fontColor: '#666666',
    alignment: 'right',
  });
  inputData['docDate'] = `Date: ${formatDate(data.meta.documentDate)}`;

  y += LH_SM + 2;

  // --- Header divider ---
  schemas.push({
    name: 'headerLine',
    type: 'line',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: 0.5,
    color: '#333333',
  });
  y += 3;

  // --- Address blocks: Bill To / Ship To ---
  const billToText = partyBlock(data.billTo);
  const shipToText = partyBlock(data.shipTo);
  const addrHeight = Math.max(
    billToText.split('\n').length * LH_SM,
    shipToText.split('\n').length * LH_SM,
    LH_SM * 4,
  );

  if (billToText) {
    schemas.push({
      name: 'billToLabel',
      type: 'text',
      position: { x: MARGIN, y },
      width: COL_W,
      height: LH_XS + 1,
      fontSize: FONT_XS,
      fontColor: '#888888',
    });
    inputData['billToLabel'] = 'BILL TO';

    schemas.push({
      name: 'billToAddr',
      type: 'text',
      position: { x: MARGIN, y: y + LH_XS + 1 },
      width: COL_W,
      height: addrHeight,
      fontSize: FONT_SM,
      fontColor: '#333333',
      lineHeight: 1.4,
    });
    inputData['billToAddr'] = billToText;
  }

  if (shipToText) {
    schemas.push({
      name: 'shipToLabel',
      type: 'text',
      position: { x: MARGIN + COL_W + 4, y },
      width: COL_W,
      height: LH_XS + 1,
      fontSize: FONT_XS,
      fontColor: '#888888',
    });
    inputData['shipToLabel'] = 'SHIP TO';

    schemas.push({
      name: 'shipToAddr',
      type: 'text',
      position: { x: MARGIN + COL_W + 4, y: y + LH_XS + 1 },
      width: COL_W,
      height: addrHeight,
      fontSize: FONT_SM,
      fontColor: '#333333',
      lineHeight: 1.4,
    });
    inputData['shipToAddr'] = shipToText;
  }

  // --- Meta fields (right column) ---
  const metaFields: [string, string | undefined][] = [
    ['Terms', data.meta.terms],
    ['Status', data.meta.status],
    ['Cust PO#', data.meta.customerPO],
    ['Sales ID', data.meta.salesId],
    ['Ship Via', data.meta.shipVia],
    ['FOB', data.meta.fob],
  ];
  const activeMetaFields = metaFields.filter(([, v]) => v);

  if (activeMetaFields.length > 0) {
    const metaText = activeMetaFields.map(([label, val]) => `${label}: ${val}`).join('\n');
    schemas.push({
      name: 'metaFields',
      type: 'text',
      position: { x: MARGIN + COL_W * 2 + 8, y: y + LH_XS + 1 },
      width: COL_W - 8,
      height: addrHeight,
      fontSize: FONT_SM,
      fontColor: '#333333',
      lineHeight: 1.5,
    });
    inputData['metaFields'] = metaText;
  }

  y += LH_XS + 1 + addrHeight + 3;

  // --- Comments ---
  if (data.comments?.public) {
    schemas.push({
      name: 'comments',
      type: 'text',
      position: { x: MARGIN, y },
      width: CONTENT_W,
      height: LH_SM * 2,
      fontSize: FONT_SM,
      fontColor: '#555555',
      lineHeight: 1.3,
    });
    inputData['comments'] = data.comments.public;
    y += LH_SM * 2 + 2;
  }

  // --- Line items divider ---
  schemas.push({
    name: 'linesDivider',
    type: 'line',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: 0.3,
    color: '#CCCCCC',
  });
  y += 1;

  // --- Line items header ---
  const colWidths = showPrices
    ? { qty: 14, item: 22, desc: CONTENT_W - 14 - 22 - 20 - 22 - 24, msrp: 20, unit: 22, ext: 24 }
    : { qty: 16, item: 30, desc: CONTENT_W - 16 - 30 };

  // Header background
  schemas.push({
    name: 'lineHeaderBg',
    type: 'rectangle',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: LH_SM + 2,
    color: '#F0F0F0',
    borderColor: '#999999',
    borderWidth: 0,
  });

  const headerLabels = showPrices
    ? ['Qty', 'Item #', 'Description', 'MSRP', 'Unit', 'Extended']
    : ['Qty', 'Item #', 'Description'];

  let hx = MARGIN;
  const headerWidths = showPrices
    ? [colWidths.qty, colWidths.item, colWidths.desc, colWidths.msrp, colWidths.unit, colWidths.ext]
    : [colWidths.qty, colWidths.item, colWidths.desc];

  headerLabels.forEach((label, i) => {
    const isRight = showPrices && i >= 3;
    schemas.push({
      name: `lineHdr_${i}`,
      type: 'text',
      position: { x: hx + 1, y: y + 0.5 },
      width: headerWidths[i] - 2,
      height: LH_SM + 1,
      fontSize: FONT_XS,
      fontColor: '#333333',
      alignment: isRight ? 'right' : 'left',
    });
    inputData[`lineHdr_${i}`] = label;
    hx += headerWidths[i];
  });

  y += LH_SM + 2;

  // --- Line items rows ---
  const maxLines = Math.min(data.lines.length, 40); // safety cap per page
  const isInvoice = data.meta.documentType === 'invoice';

  for (let i = 0; i < maxLines; i++) {
    const ln = data.lines[i];
    const rowY = y + i * (LH_SM + 1.5);

    // Check if we're near bottom of page
    if (rowY > PAGE_H - MARGIN - 40) break;

    let rx = MARGIN;
    const qty = isInvoice ? (ln.qtyShipped ?? ln.qty ?? 0) : (ln.qtyOrdered ?? ln.qty ?? 0);

    const rowData = showPrices
      ? [
          String(qty),
          ln.itemNum || '',
          ln.description || '',
          fmtMoney(ln.msrp || ln.unitPrice),
          fmtMoney(ln.discountedPrice || ln.unitPrice),
          fmtMoney(ln.extendedPrice),
        ]
      : [String(qty), ln.itemNum || '', ln.description || ''];

    rowData.forEach((val, j) => {
      const isRight = showPrices && j >= 3;
      schemas.push({
        name: `line_${i}_${j}`,
        type: 'text',
        position: { x: rx + 1, y: rowY },
        width: headerWidths[j] - 2,
        height: LH_SM + 1,
        fontSize: FONT_SM,
        fontColor: '#222222',
        alignment: isRight ? 'right' : 'left',
      });
      inputData[`line_${i}_${j}`] = val;
      rx += headerWidths[j];
    });

    // Row bottom border
    schemas.push({
      name: `lineRowBorder_${i}`,
      type: 'line',
      position: { x: MARGIN, y: rowY + LH_SM + 1 },
      width: CONTENT_W,
      height: 0.2,
      color: '#DDDDDD',
    });
  }

  // Position after lines
  const linesEndY = y + maxLines * (LH_SM + 1.5) + 2;
  y = Math.min(linesEndY, PAGE_H - MARGIN - 35);

  // --- Bottom divider ---
  schemas.push({
    name: 'bottomDivider',
    type: 'line',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: 0.5,
    color: '#999999',
  });
  y += 3;

  // --- Totals (right side) ---
  if (showPrices) {
    const totalsX = MARGIN + CONTENT_W - 70;
    const totalsW = 70;
    const totLines: [string, string][] = [
      ['Sales Amount', fmtMoney(data.totals.salesAmount || data.totals.subtotal)],
      ['Sales Tax', fmtMoney(data.totals.salesTax)],
      ['Shipping', fmtMoney((data.totals.shipping || 0) + (data.totals.handling || 0))],
    ];

    totLines.forEach(([label, val], i) => {
      const ty = y + i * (LH_SM + 1);
      schemas.push({
        name: `totLabel_${i}`,
        type: 'text',
        position: { x: totalsX, y: ty },
        width: totalsW * 0.55,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#666666',
      });
      inputData[`totLabel_${i}`] = label;

      schemas.push({
        name: `totVal_${i}`,
        type: 'text',
        position: { x: totalsX + totalsW * 0.55, y: ty },
        width: totalsW * 0.45,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#222222',
        alignment: 'right',
      });
      inputData[`totVal_${i}`] = val;
    });

    const totY = y + totLines.length * (LH_SM + 1);

    // Total line
    schemas.push({
      name: 'totalLine',
      type: 'line',
      position: { x: totalsX, y: totY },
      width: totalsW,
      height: 0.5,
      color: '#333333',
    });

    schemas.push({
      name: 'totalLabel',
      type: 'text',
      position: { x: totalsX, y: totY + 1 },
      width: totalsW * 0.55,
      height: LH_MD,
      fontSize: FONT_MD,
      fontColor: '#111111',
    });
    inputData['totalLabel'] = `${typeLabel} Total`;

    schemas.push({
      name: 'totalVal',
      type: 'text',
      position: { x: totalsX + totalsW * 0.55, y: totY + 1 },
      width: totalsW * 0.45,
      height: LH_MD,
      fontSize: FONT_MD,
      fontColor: '#111111',
      alignment: 'right',
    });
    inputData['totalVal'] = fmtMoney(data.totals.total);

    // Balance due
    if (data.totals.balanceDue !== undefined) {
      schemas.push({
        name: 'balLabel',
        type: 'text',
        position: { x: totalsX, y: totY + LH_MD + 2 },
        width: totalsW * 0.55,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#333333',
      });
      inputData['balLabel'] = 'Balance Due';

      schemas.push({
        name: 'balVal',
        type: 'text',
        position: { x: totalsX + totalsW * 0.55, y: totY + LH_MD + 2 },
        width: totalsW * 0.45,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#333333',
        alignment: 'right',
      });
      inputData['balVal'] = fmtMoney(data.totals.balanceDue);
    }

    // Thank you (left side, same level as totals)
    schemas.push({
      name: 'thankYou',
      type: 'text',
      position: { x: MARGIN, y },
      width: CONTENT_W - 80,
      height: LH_MD,
      fontSize: FONT_SM,
      fontColor: '#333333',
    });
    inputData['thankYou'] = 'Thank you for your business.';
  }

  // --- Footer ---
  const footerY = PAGE_H - MARGIN - 5;
  schemas.push({
    name: 'footerLine',
    type: 'line',
    position: { x: MARGIN, y: footerY - 2 },
    width: CONTENT_W,
    height: 0.2,
    color: '#DDDDDD',
  });

  schemas.push({
    name: 'footerLeft',
    type: 'text',
    position: { x: MARGIN, y: footerY },
    width: CONTENT_W * 0.33,
    height: LH_XS,
    fontSize: FONT_XS,
    fontColor: '#888888',
  });
  inputData['footerLeft'] = `${typeLabel}# ${data.meta.documentNumber}`;

  schemas.push({
    name: 'footerCenter',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.33, y: footerY },
    width: CONTENT_W * 0.34,
    height: LH_XS,
    fontSize: FONT_XS,
    fontColor: '#888888',
    alignment: 'center',
  });
  inputData['footerCenter'] = 'Generated by WebClerk';

  schemas.push({
    name: 'footerRight',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.67, y: footerY },
    width: CONTENT_W * 0.33,
    height: LH_XS,
    fontSize: FONT_XS,
    fontColor: '#888888',
    alignment: 'right',
  });
  inputData['footerRight'] = `Customer# ${data.meta.customerId || ''}`;

  const template: Template = {
    basePdf: {
      width: PAGE_W,
      height: PAGE_H,
      padding: [0, 0, 0, 0], // we handle margins ourselves
    },
    schemas: [schemas],
  };

  return { template, inputs: [inputData] };
}

// ---------------------------------------------------------------------------
// Statement template builder
// ---------------------------------------------------------------------------

function buildStatementTemplate(data: StatementData): { template: Template; inputs: Record<string, string>[] } {
  const schemas: Record<string, any>[] = [];
  const inputData: Record<string, string> = {};
  let y = MARGIN;

  // Company header
  schemas.push({
    name: 'companyName',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.5,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#111111',
  });
  inputData['companyName'] = data.company.name;

  schemas.push({
    name: 'stmtTitle',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.5, y },
    width: CONTENT_W * 0.5,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#333333',
    alignment: 'right',
  });
  inputData['stmtTitle'] = `Statement: ${data.statement_date}`;

  y += LH_LG + 3;

  // Company address
  const coAddr = [data.company.address, data.company.city_state_zip, data.company.phone]
    .filter(Boolean).join('\n');
  schemas.push({
    name: 'companyAddr',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.4,
    height: LH_SM * 3,
    fontSize: FONT_SM,
    fontColor: '#555555',
    lineHeight: 1.4,
  });
  inputData['companyAddr'] = coAddr;
  y += LH_SM * 3 + 4;

  // Header divider
  schemas.push({
    name: 'headerLine',
    type: 'line',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: 0.5,
    color: '#333333',
  });
  y += 3;

  // Customer info
  const custText = partyBlock(data.customer);
  schemas.push({
    name: 'custLabel',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.45,
    height: LH_XS + 1,
    fontSize: FONT_XS,
    fontColor: '#888888',
  });
  inputData['custLabel'] = 'CUSTOMER';

  schemas.push({
    name: 'custAddr',
    type: 'text',
    position: { x: MARGIN, y: y + LH_XS + 1 },
    width: CONTENT_W * 0.45,
    height: LH_SM * 6,
    fontSize: FONT_SM,
    fontColor: '#333333',
    lineHeight: 1.4,
  });
  inputData['custAddr'] = custText;

  // Message
  schemas.push({
    name: 'message',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.5, y: y + LH_XS + 1 },
    width: CONTENT_W * 0.5,
    height: LH_SM * 6,
    fontSize: FONT_XS,
    fontColor: '#555555',
    lineHeight: 1.5,
  });
  inputData['message'] = data.message || 'Our records show that we have yet to receive payments for the invoice(s) listed below.';

  y += LH_XS + 1 + LH_SM * 6 + 4;

  // Aging summary header
  const agingCols = ['', 'Balance Due', 'Current', '1-30 Days', '31-60 Days', '61+ Days'];
  const agingColW = CONTENT_W / agingCols.length;

  // Aging header background
  schemas.push({
    name: 'agingBg',
    type: 'rectangle',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: LH_SM + 2,
    color: '#F0F0F0',
  });

  agingCols.forEach((label, i) => {
    schemas.push({
      name: `agHdr_${i}`,
      type: 'text',
      position: { x: MARGIN + i * agingColW + 1, y: y + 0.5 },
      width: agingColW - 2,
      height: LH_SM + 1,
      fontSize: FONT_XS,
      fontColor: '#333333',
      alignment: i === 0 ? 'left' : 'right',
    });
    inputData[`agHdr_${i}`] = label;
  });

  y += LH_SM + 2;

  // Aging values
  const agingVals = [
    'Totals:',
    fmtMoney(data.aging_summary.balance_due),
    fmtMoney(data.aging_summary.current),
    fmtMoney(data.aging_summary.past_1_30),
    fmtMoney(data.aging_summary.past_31_60),
    fmtMoney(data.aging_summary.past_61),
  ];

  agingVals.forEach((val, i) => {
    schemas.push({
      name: `agVal_${i}`,
      type: 'text',
      position: { x: MARGIN + i * agingColW + 1, y },
      width: agingColW - 2,
      height: LH_SM + 1,
      fontSize: FONT_SM,
      fontColor: '#111111',
      alignment: i === 0 ? 'right' : 'right',
    });
    inputData[`agVal_${i}`] = val;
  });

  y += LH_SM + 4;

  // Transaction detail header
  schemas.push({
    name: 'txnLabel',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: LH_MD,
    fontSize: FONT_MD,
    fontColor: '#111111',
  });
  inputData['txnLabel'] = 'Transaction Details:';
  y += LH_MD + 2;

  // Transaction columns
  const txnCols = ['Type', 'Number', 'Date', 'Total', 'Balance', 'Current', '1-30', '31-60', '61+', 'Finance', 'Days'];
  const txnColW = CONTENT_W / txnCols.length;

  // Header bg
  schemas.push({
    name: 'txnHdrBg',
    type: 'rectangle',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: LH_SM + 1,
    color: '#F0F0F0',
  });

  txnCols.forEach((label, i) => {
    schemas.push({
      name: `txnHdr_${i}`,
      type: 'text',
      position: { x: MARGIN + i * txnColW + 0.5, y: y + 0.3 },
      width: txnColW - 1,
      height: LH_SM,
      fontSize: 6,
      fontColor: '#333333',
      alignment: i >= 3 ? 'right' : 'left',
    });
    inputData[`txnHdr_${i}`] = label;
  });

  y += LH_SM + 1;

  // Transaction rows
  const maxRows = Math.min(data.lines.length, 35);
  for (let r = 0; r < maxRows; r++) {
    const ln = data.lines[r];
    const rowY = y + r * (LH_XS + 1.5);
    if (rowY > PAGE_H - MARGIN - 10) break;

    const vals = [
      ln.type, ln.number, ln.date,
      fmtMoney(ln.total), fmtMoney(ln.balance),
      fmtMoney(ln.current), fmtMoney(ln.past_1_30),
      fmtMoney(ln.past_31_60), fmtMoney(ln.past_61),
      fmtMoney(ln.finance), String(ln.days),
    ];

    vals.forEach((val, i) => {
      schemas.push({
        name: `txn_${r}_${i}`,
        type: 'text',
        position: { x: MARGIN + i * txnColW + 0.5, y: rowY },
        width: txnColW - 1,
        height: LH_XS + 1,
        fontSize: 6,
        fontColor: '#222222',
        alignment: i >= 3 ? 'right' : 'left',
      });
      inputData[`txn_${r}_${i}`] = val;
    });
  }

  // Footer
  const footerY = PAGE_H - MARGIN - 5;
  schemas.push({
    name: 'footer',
    type: 'text',
    position: { x: MARGIN, y: footerY },
    width: CONTENT_W,
    height: LH_XS,
    fontSize: FONT_XS,
    fontColor: '#888888',
    alignment: 'center',
  });
  inputData['footer'] = `Statement generated by WebClerk — ${data.statement_date}`;

  const template: Template = {
    basePdf: { width: PAGE_W, height: PAGE_H, padding: [0, 0, 0, 0] },
    schemas: [schemas],
  };

  return { template, inputs: [inputData] };
}

// ---------------------------------------------------------------------------
// Proposal template builder — WC2 heritage layout
// ---------------------------------------------------------------------------

function buildProposalTemplate(data: CommercePdfData): { template: Template; inputs: Record<string, string>[] } {
  const schemas: Record<string, any>[] = [];
  const inputData: Record<string, string> = {};
  const showPrices = data.showPrices !== false;
  let y = MARGIN;

  // --- Company name + Proposal title ---
  schemas.push({
    name: 'companyName',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.55,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#111111',
  });
  inputData['companyName'] = data.companyName;

  schemas.push({
    name: 'docTitle',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.55, y },
    width: CONTENT_W * 0.45,
    height: LH_LG + 2,
    fontSize: FONT_LG,
    fontColor: '#333333',
    alignment: 'right',
  });
  inputData['docTitle'] = `Proposal`;

  y += LH_LG + 2;

  schemas.push({
    name: 'docNum',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.55, y },
    width: CONTENT_W * 0.45,
    height: LH_MD + 1,
    fontSize: FONT_MD + 2,
    fontColor: '#333333',
    alignment: 'right',
  });
  inputData['docNum'] = data.meta.documentNumber;

  // Company detail
  const coDetail = [data.companyAddress, data.companyPhone ? `Phone: ${data.companyPhone}` : '', data.companyFax ? `FAX: ${data.companyFax}` : '']
    .filter(Boolean).join(' • ');
  if (coDetail) {
    schemas.push({
      name: 'coDetail',
      type: 'text',
      position: { x: MARGIN, y },
      width: CONTENT_W * 0.55,
      height: LH_XS + 1,
      fontSize: FONT_XS,
      fontColor: '#555555',
    });
    inputData['coDetail'] = coDetail;
  }

  y += LH_MD + 3;

  // Header divider
  schemas.push({
    name: 'headerLine',
    type: 'line',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: 0.5,
    color: '#444444',
  });
  y += 3;

  // --- Proposed To + Account/Terms + Dates (3-column) ---
  const proposedToText = partyBlock(data.billTo);
  const addrHeight = Math.max(proposedToText.split('\n').length * LH_SM, LH_SM * 5);

  // Proposed To
  schemas.push({
    name: 'proposedLabel',
    type: 'text',
    position: { x: MARGIN, y },
    width: CONTENT_W * 0.35,
    height: LH_XS + 1,
    fontSize: FONT_XS,
    fontColor: '#888888',
  });
  inputData['proposedLabel'] = 'Proposed to:';

  schemas.push({
    name: 'proposedAddr',
    type: 'text',
    position: { x: MARGIN, y: y + LH_XS + 1 },
    width: CONTENT_W * 0.35,
    height: addrHeight,
    fontSize: FONT_SM,
    fontColor: '#333333',
    lineHeight: 1.4,
  });
  inputData['proposedAddr'] = proposedToText;

  // Contact info below address
  const contactParts: string[] = [];
  if (data.billTo?.phone) contactParts.push(`Phone: ${data.billTo.phone}`);
  if (data.billTo?.email) contactParts.push(`Email: ${data.billTo.email}`);
  if (contactParts.length) {
    schemas.push({
      name: 'contactInfo',
      type: 'text',
      position: { x: MARGIN, y: y + LH_XS + 1 + addrHeight },
      width: CONTENT_W * 0.35,
      height: LH_SM * 2,
      fontSize: FONT_SM,
      fontColor: '#333333',
      lineHeight: 1.4,
    });
    inputData['contactInfo'] = contactParts.join('\n');
  }

  // Account/Terms box (center)
  const metaBoxX = MARGIN + CONTENT_W * 0.38;
  const metaBoxW = CONTENT_W * 0.32;

  schemas.push({
    name: 'metaBox',
    type: 'rectangle',
    position: { x: metaBoxX, y },
    width: metaBoxW,
    height: addrHeight + LH_XS + 2,
    color: '#FFFFFF',
    borderColor: '#CCCCCC',
    borderWidth: 0.3,
  });

  const metaRows: [string, string][] = [];
  if (data.meta.customerId) metaRows.push(['Account', String(data.meta.customerId)]);
  if (data.meta.terms) metaRows.push(['Terms', data.meta.terms]);
  if (data.meta.salesId) metaRows.push(['Salesperson', data.meta.salesId]);
  if (data.repId) metaRows.push(['Rep', data.repId]);
  if (data.meta.shipVia) metaRows.push(['Ship Via', data.meta.shipVia]);
  if (data.meta.typeSale) metaRows.push(['Type Sale', data.meta.typeSale]);

  metaRows.forEach(([label, val], i) => {
    schemas.push({
      name: `metaL_${i}`,
      type: 'text',
      position: { x: metaBoxX + 2, y: y + 2 + i * (LH_SM + 0.5) },
      width: metaBoxW * 0.4,
      height: LH_SM,
      fontSize: FONT_SM,
      fontColor: '#666666',
    });
    inputData[`metaL_${i}`] = label;

    schemas.push({
      name: `metaV_${i}`,
      type: 'text',
      position: { x: metaBoxX + metaBoxW * 0.42, y: y + 2 + i * (LH_SM + 0.5) },
      width: metaBoxW * 0.55,
      height: LH_SM,
      fontSize: FONT_SM,
      fontColor: '#222222',
    });
    inputData[`metaV_${i}`] = val;
  });

  // Dates box (right)
  const dateBoxX = MARGIN + CONTENT_W * 0.72;
  const dateBoxW = CONTENT_W * 0.28;

  schemas.push({
    name: 'dateBox',
    type: 'rectangle',
    position: { x: dateBoxX, y },
    width: dateBoxW,
    height: addrHeight + LH_XS + 2,
    color: '#FFFFFF',
    borderColor: '#CCCCCC',
    borderWidth: 0.3,
  });

  const dateRows: [string, string][] = [
    ['Proposed', formatDate(data.meta.documentDate)],
  ];
  if (data.daysValidFor !== undefined) dateRows.push(['Valid days', String(data.daysValidFor)]);
  if (data.meta.dateNeeded) dateRows.push(['Date Needed', formatDate(data.meta.dateNeeded)]);
  if (data.daysLeadTime && data.daysLeadTime > 0) dateRows.push(['Lead Time', `${data.daysLeadTime} days`]);

  dateRows.forEach(([label, val], i) => {
    schemas.push({
      name: `dateL_${i}`,
      type: 'text',
      position: { x: dateBoxX + 2, y: y + 2 + i * (LH_SM + 0.5) },
      width: dateBoxW * 0.5,
      height: LH_SM,
      fontSize: FONT_SM,
      fontColor: '#666666',
    });
    inputData[`dateL_${i}`] = label;

    schemas.push({
      name: `dateV_${i}`,
      type: 'text',
      position: { x: dateBoxX + dateBoxW * 0.52, y: y + 2 + i * (LH_SM + 0.5) },
      width: dateBoxW * 0.45,
      height: LH_SM,
      fontSize: FONT_SM,
      fontColor: '#222222',
    });
    inputData[`dateV_${i}`] = val;
  });

  y += addrHeight + LH_XS + 5;

  // --- Line items: Accept | Use | Item | Desc | Qty | Base | Disc% | Unit | Ext ---
  const colW = showPrices
    ? { accept: 12, use: 8, item: 22, desc: CONTENT_W - 12 - 8 - 22 - 12 - 18 - 14 - 20 - 22, qty: 12, base: 18, disc: 14, unit: 20, ext: 22 }
    : { accept: 14, use: 10, item: 28, desc: CONTENT_W - 14 - 10 - 28 };

  // Header bg
  schemas.push({
    name: 'lineHdrBg',
    type: 'rectangle',
    position: { x: MARGIN, y },
    width: CONTENT_W,
    height: LH_SM + 2,
    color: '#F0F0F0',
  });

  const proposalHeaders = showPrices
    ? ['Accept', 'Use', 'Item Num', 'Description', 'Qty', 'Base', 'Disc %', 'Unit Price', 'Ext Price']
    : ['Accept', 'Use', 'Item Num', 'Description'];
  const proposalWidths = showPrices
    ? [colW.accept, colW.use, colW.item, colW.desc, colW.qty, colW.base, colW.disc, colW.unit, colW.ext]
    : [colW.accept, colW.use, colW.item, colW.desc];

  let hx = MARGIN;
  proposalHeaders.forEach((label, i) => {
    const isRight = showPrices && i >= 4;
    schemas.push({
      name: `plHdr_${i}`,
      type: 'text',
      position: { x: hx + 0.5, y: y + 0.5 },
      width: proposalWidths[i] - 1,
      height: LH_SM + 1,
      fontSize: FONT_XS,
      fontColor: '#333333',
      alignment: i <= 1 ? 'center' : isRight ? 'right' : 'left',
    });
    inputData[`plHdr_${i}`] = label;
    hx += proposalWidths[i];
  });

  y += LH_SM + 2;

  // Line rows
  const maxLines = Math.min(data.lines.length, 30);
  for (let i = 0; i < maxLines; i++) {
    const ln = data.lines[i];
    const rowY = y + i * (LH_SM + 1.5);
    if (rowY > PAGE_H - MARGIN - 50) break;

    const isUsed = ln.use !== false;
    const basePrice = ln.basePrice || ln.msrp || ln.unitPrice || 0;
    const discPct = ln.discountPct || ln.discount || 0;
    const unitPrice = ln.discountedPrice || ln.unitPrice || 0;
    const extPrice = ln.extendedPrice || 0;

    const rowVals = showPrices
      ? ['', isUsed ? 'x' : '', ln.itemNum || '', ln.description || '',
         String(ln.qty || ln.qtyOrdered || 0), fmtMoney(basePrice),
         discPct > 0 ? discPct.toFixed(1) : '', fmtMoney(unitPrice),
         extPrice > 0 ? fmtMoney(extPrice) : '']
      : ['', isUsed ? 'x' : '', ln.itemNum || '', ln.description || ''];

    let rx = MARGIN;
    rowVals.forEach((val, j) => {
      const isRight = showPrices && j >= 4;
      schemas.push({
        name: `pl_${i}_${j}`,
        type: 'text',
        position: { x: rx + 0.5, y: rowY },
        width: proposalWidths[j] - 1,
        height: LH_SM + 1,
        fontSize: FONT_SM,
        fontColor: '#222222',
        alignment: j <= 1 ? 'center' : isRight ? 'right' : 'left',
      });
      inputData[`pl_${i}_${j}`] = val;
      rx += proposalWidths[j];
    });

    // Row border
    schemas.push({
      name: `plBorder_${i}`,
      type: 'line',
      position: { x: MARGIN, y: rowY + LH_SM + 1 },
      width: CONTENT_W,
      height: 0.2,
      color: '#DDDDDD',
    });
  }

  y = y + maxLines * (LH_SM + 1.5) + 3;
  y = Math.min(y, PAGE_H - MARGIN - 55);

  // --- Comments + Totals ---
  // Comments (left)
  if (data.comments?.public) {
    schemas.push({
      name: 'propComments',
      type: 'text',
      position: { x: MARGIN, y },
      width: CONTENT_W - 75,
      height: LH_SM * 4,
      fontSize: FONT_SM,
      fontColor: '#333333',
      lineHeight: 1.4,
    });
    inputData['propComments'] = data.comments.public;
  }

  // Totals (right)
  if (showPrices) {
    const totX = MARGIN + CONTENT_W - 70;
    const totW = 70;

    const totRows: [string, string][] = [
      ['* Amount', fmtMoney(data.totals.salesAmount || data.totals.subtotal)],
      ['Sales Tax', fmtMoney(data.totals.salesTax || 0)],
      ['Shipping', fmtMoney(data.totals.shipping || 0)],
    ];

    totRows.forEach(([label, val], i) => {
      schemas.push({
        name: `ptL_${i}`,
        type: 'text',
        position: { x: totX, y: y + i * (LH_SM + 0.5) },
        width: totW * 0.5,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#666666',
      });
      inputData[`ptL_${i}`] = label;

      schemas.push({
        name: `ptV_${i}`,
        type: 'text',
        position: { x: totX + totW * 0.5, y: y + i * (LH_SM + 0.5) },
        width: totW * 0.5,
        height: LH_SM,
        fontSize: FONT_SM,
        fontColor: '#222222',
        alignment: 'right',
      });
      inputData[`ptV_${i}`] = val;
    });

    const totY = y + totRows.length * (LH_SM + 0.5);
    schemas.push({
      name: 'propTotLine',
      type: 'line',
      position: { x: totX, y: totY },
      width: totW,
      height: 0.5,
      color: '#333333',
    });

    schemas.push({
      name: 'propTotLabel',
      type: 'text',
      position: { x: totX, y: totY + 1 },
      width: totW * 0.5,
      height: LH_MD,
      fontSize: FONT_MD,
      fontColor: '#111111',
    });
    inputData['propTotLabel'] = 'Total';

    schemas.push({
      name: 'propTotVal',
      type: 'text',
      position: { x: totX + totW * 0.5, y: totY + 1 },
      width: totW * 0.5,
      height: LH_MD,
      fontSize: FONT_MD,
      fontColor: '#111111',
      alignment: 'right',
    });
    inputData['propTotVal'] = fmtMoney(data.totals.total);

    // Footnote
    schemas.push({
      name: 'amtNote',
      type: 'text',
      position: { x: totX, y: totY + LH_MD + 2 },
      width: totW,
      height: LH_XS + 1,
      fontSize: 6,
      fontColor: '#888888',
    });
    inputData['amtNote'] = '* Amount total is of the use (x) items only.';
  }

  // --- Dual Signature Block ---
  const sigY = PAGE_H - MARGIN - 22;

  // Customer acceptance (left)
  schemas.push({
    name: 'sigInstruct',
    type: 'text',
    position: { x: MARGIN, y: sigY - 8 },
    width: CONTENT_W * 0.5,
    height: LH_SM * 2,
    fontSize: FONT_XS,
    fontColor: '#666666',
    lineHeight: 1.4,
  });
  inputData['sigInstruct'] = 'Please initial (in the Accept column) each line item you are purchasing.';

  schemas.push({
    name: 'sigLine1',
    type: 'line',
    position: { x: MARGIN, y: sigY },
    width: CONTENT_W * 0.4,
    height: 0.3,
    color: '#444444',
  });

  schemas.push({
    name: 'acceptedLabel',
    type: 'text',
    position: { x: MARGIN, y: sigY + 1 },
    width: CONTENT_W * 0.4,
    height: LH_SM,
    fontSize: FONT_SM,
    fontColor: '#555555',
  });
  const custName = data.billTo?.company || [data.billTo?.firstName, data.billTo?.lastName].filter(Boolean).join(' ') || '';
  inputData['acceptedLabel'] = `Accepted  ${custName}`;

  schemas.push({
    name: 'dateLabel',
    type: 'text',
    position: { x: MARGIN, y: sigY + LH_SM + 2 },
    width: 20,
    height: LH_SM,
    fontSize: FONT_SM,
    fontColor: '#555555',
  });
  inputData['dateLabel'] = 'Date';

  schemas.push({
    name: 'sigLine2',
    type: 'line',
    position: { x: MARGIN + 20, y: sigY + LH_SM + 2 + LH_SM },
    width: CONTENT_W * 0.25,
    height: 0.3,
    color: '#444444',
  });

  // Company approval (right)
  schemas.push({
    name: 'approvedLine',
    type: 'line',
    position: { x: MARGIN + CONTENT_W * 0.65, y: sigY },
    width: CONTENT_W * 0.35,
    height: 0.3,
    color: '#444444',
  });

  schemas.push({
    name: 'approvedLabel',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.65, y: sigY + 1 },
    width: CONTENT_W * 0.35,
    height: LH_SM,
    fontSize: FONT_SM,
    fontColor: '#555555',
    alignment: 'right',
  });
  inputData['approvedLabel'] = `Approved  ${data.companyName}`;

  schemas.push({
    name: 'approvedDate',
    type: 'text',
    position: { x: MARGIN + CONTENT_W * 0.65, y: sigY + LH_SM + 2 },
    width: CONTENT_W * 0.35,
    height: LH_SM,
    fontSize: FONT_SM,
    fontColor: '#333333',
    alignment: 'right',
  });
  inputData['approvedDate'] = formatDate(data.meta.documentDate);

  const template: Template = {
    basePdf: { width: PAGE_W, height: PAGE_H, padding: [0, 0, 0, 0] },
    schemas: [schemas],
  };

  return { template, inputs: [inputData] };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Generate a PDF for a transaction document (invoice, order, proposal, etc.).
 * Returns Uint8Array of PDF bytes.
 */
export async function generateTransactionPdf(data: CommercePdfData): Promise<Uint8Array> {
  // Proposal gets its own template with Accept/Use columns and WC2 layout
  const { template, inputs } = data.meta.documentType === 'proposal'
    ? buildProposalTemplate(data)
    : buildTransactionTemplate(data);

  const pdf = await generate({
    template,
    inputs,
    plugins: { text, line, rectangle, image },
  });

  return pdf;
}

/**
 * Generate a PDF for a customer statement.
 * Returns Uint8Array of PDF bytes.
 */
export async function generateStatementPdf(data: StatementData): Promise<Uint8Array> {
  const { template, inputs } = buildStatementTemplate(data);

  const pdf = await generate({
    template,
    inputs,
    plugins: { text, line, rectangle, image },
  });

  return pdf;
}

/**
 * Generate and immediately trigger download.
 */
export async function downloadTransactionPdf(data: CommercePdfData): Promise<void> {
  const pdfBytes = await generateTransactionPdf(data);
  triggerDownload(pdfBytes, makeFilename(data.meta));
}

export async function downloadStatementPdf(data: StatementData): Promise<void> {
  const pdfBytes = await generateStatementPdf(data);
  triggerDownload(pdfBytes, `Statement_${data.statement_date}.pdf`);
}

/**
 * Generate and return as Blob (for email attachment, preview, etc.)
 */
export async function generateTransactionPdfBlob(data: CommercePdfData): Promise<Blob> {
  const pdfBytes = await generateTransactionPdf(data);
  return new Blob([pdfBytes], { type: 'application/pdf' });
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function makeFilename(meta: PrintDocumentMeta): string {
  const typeLabel = DOCUMENT_TYPE_LABELS[meta.documentType] || meta.documentType;
  const slug = typeLabel.replace(/\s+/g, '_');
  const dateStr = new Date().toISOString().split('T')[0];
  return `${slug}_${meta.documentNumber || 'draft'}_${dateStr}.pdf`;
}

function triggerDownload(bytes: Uint8Array, filename: string): void {
  const blob = new Blob([bytes], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
