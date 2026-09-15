/**
 * defaultReportTemplates.ts — Default pdfme templates for common WC3 reports.
 *
 * Each template uses BLANK_PDF (letter size 8.5x11) from @pdfme/common.
 * Field names match wcapi record field names so ReportViewer can map directly.
 *
 * Templates: Invoice, Pick List, Purchase Order, Order Confirmation.
 */
import { BLANK_PDF } from '@pdfme/common';
import type { Template } from '@pdfme/common';

// -- Shared header fields (company info populated from primary_organization Setting)
const companyHeaderFields = [
  {
    name: 'company_name',
    type: 'text' as const,
    position: { x: 14, y: 10 },
    width: 120,
    height: 10,
    fontSize: 18,
    fontWeight: 'bold' as const,
    fontColor: '#1a1a1a',
  },
  {
    name: 'company_address',
    type: 'text' as const,
    position: { x: 14, y: 22 },
    width: 120,
    height: 8,
    fontSize: 9,
    fontColor: '#555555',
  },
  {
    name: 'company_phone',
    type: 'text' as const,
    position: { x: 14, y: 30 },
    width: 120,
    height: 8,
    fontSize: 9,
    fontColor: '#555555',
  },
];

// -- Bill-to address block
const billToFields = [
  {
    name: 'bill_to_label',
    type: 'text' as const,
    position: { x: 14, y: 52 },
    width: 40,
    height: 7,
    fontSize: 9,
    fontWeight: 'bold' as const,
    fontColor: '#333333',
  },
  {
    name: 'bill_to_name',
    type: 'text' as const,
    position: { x: 14, y: 59 },
    width: 80,
    height: 7,
    fontSize: 10,
  },
  {
    name: 'bill_to_address',
    type: 'text' as const,
    position: { x: 14, y: 66 },
    width: 80,
    height: 14,
    fontSize: 9,
    fontColor: '#333333',
  },
];

// -- Ship-to address block
const shipToFields = [
  {
    name: 'ship_to_label',
    type: 'text' as const,
    position: { x: 110, y: 52 },
    width: 40,
    height: 7,
    fontSize: 9,
    fontWeight: 'bold' as const,
    fontColor: '#333333',
  },
  {
    name: 'ship_to_name',
    type: 'text' as const,
    position: { x: 110, y: 59 },
    width: 80,
    height: 7,
    fontSize: 10,
  },
  {
    name: 'ship_to_address',
    type: 'text' as const,
    position: { x: 110, y: 66 },
    width: 80,
    height: 14,
    fontSize: 9,
    fontColor: '#333333',
  },
];

// ============================================================================
// Invoice
// ============================================================================
export const invoiceTemplate: Template = {
  basePdf: BLANK_PDF,
  schemas: [
    [
      ...companyHeaderFields,
      // Document title + number
      {
        name: 'document_title',
        type: 'text',
        position: { x: 150, y: 10 },
        width: 46,
        height: 12,
        fontSize: 20,
        fontWeight: 'bold',
        fontColor: '#1a1a1a',
        alignment: 'right',
      },
      {
        name: 'invoice_number',
        type: 'text',
        position: { x: 150, y: 24 },
        width: 46,
        height: 8,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'invoice_date',
        type: 'text',
        position: { x: 150, y: 32 },
        width: 46,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      {
        name: 'due_date',
        type: 'text',
        position: { x: 150, y: 40 },
        width: 46,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      // Addresses
      ...billToFields,
      ...shipToFields,
      // Line items header
      {
        name: 'line_items_header',
        type: 'text',
        position: { x: 14, y: 88 },
        width: 182,
        height: 7,
        fontSize: 8,
        fontWeight: 'bold',
        fontColor: '#ffffff',
        backgroundColor: '#333333',
      },
      // Line items (single text block — formatted by caller)
      {
        name: 'line_items',
        type: 'text',
        position: { x: 14, y: 96 },
        width: 182,
        height: 120,
        fontSize: 9,
        fontColor: '#333333',
      },
      // Totals
      {
        name: 'subtotal',
        type: 'text',
        position: { x: 140, y: 220 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'tax',
        type: 'text',
        position: { x: 140, y: 228 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'shipping',
        type: 'text',
        position: { x: 140, y: 236 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'total',
        type: 'text',
        position: { x: 140, y: 246 },
        width: 56,
        height: 9,
        fontSize: 12,
        fontWeight: 'bold',
        alignment: 'right',
      },
      // Footer
      {
        name: 'terms',
        type: 'text',
        position: { x: 14, y: 262 },
        width: 182,
        height: 10,
        fontSize: 8,
        fontColor: '#888888',
      },
      {
        name: 'notes',
        type: 'text',
        position: { x: 14, y: 272 },
        width: 182,
        height: 10,
        fontSize: 8,
        fontColor: '#888888',
      },
    ],
  ],
};

// ============================================================================
// Pick List
// ============================================================================
export const pickListTemplate: Template = {
  basePdf: BLANK_PDF,
  schemas: [
    [
      ...companyHeaderFields,
      {
        name: 'document_title',
        type: 'text',
        position: { x: 150, y: 10 },
        width: 46,
        height: 12,
        fontSize: 20,
        fontWeight: 'bold',
        fontColor: '#1a1a1a',
        alignment: 'right',
      },
      {
        name: 'order_number',
        type: 'text',
        position: { x: 150, y: 24 },
        width: 46,
        height: 8,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'order_date',
        type: 'text',
        position: { x: 150, y: 32 },
        width: 46,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      {
        name: 'customer_name',
        type: 'text',
        position: { x: 14, y: 52 },
        width: 100,
        height: 8,
        fontSize: 10,
        fontWeight: 'bold',
      },
      ...shipToFields,
      // Pick list header
      {
        name: 'pick_header',
        type: 'text',
        position: { x: 14, y: 88 },
        width: 182,
        height: 7,
        fontSize: 8,
        fontWeight: 'bold',
        fontColor: '#ffffff',
        backgroundColor: '#333333',
      },
      // Pick items (Qty | Item | Description | Location | Picked)
      {
        name: 'pick_items',
        type: 'text',
        position: { x: 14, y: 96 },
        width: 182,
        height: 160,
        fontSize: 9,
        fontColor: '#333333',
      },
      // Notes
      {
        name: 'notes',
        type: 'text',
        position: { x: 14, y: 262 },
        width: 182,
        height: 14,
        fontSize: 8,
        fontColor: '#888888',
      },
    ],
  ],
};

// ============================================================================
// Purchase Order
// ============================================================================
export const purchaseOrderTemplate: Template = {
  basePdf: BLANK_PDF,
  schemas: [
    [
      ...companyHeaderFields,
      {
        name: 'document_title',
        type: 'text',
        position: { x: 140, y: 10 },
        width: 56,
        height: 12,
        fontSize: 20,
        fontWeight: 'bold',
        fontColor: '#1a1a1a',
        alignment: 'right',
      },
      {
        name: 'po_number',
        type: 'text',
        position: { x: 140, y: 24 },
        width: 56,
        height: 8,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'po_date',
        type: 'text',
        position: { x: 140, y: 32 },
        width: 56,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      {
        name: 'expected_date',
        type: 'text',
        position: { x: 140, y: 40 },
        width: 56,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      // Vendor block
      {
        name: 'vendor_label',
        type: 'text',
        position: { x: 14, y: 52 },
        width: 40,
        height: 7,
        fontSize: 9,
        fontWeight: 'bold',
        fontColor: '#333333',
      },
      {
        name: 'vendor_name',
        type: 'text',
        position: { x: 14, y: 59 },
        width: 80,
        height: 7,
        fontSize: 10,
      },
      {
        name: 'vendor_address',
        type: 'text',
        position: { x: 14, y: 66 },
        width: 80,
        height: 14,
        fontSize: 9,
        fontColor: '#333333',
      },
      // Ship-to
      ...shipToFields,
      // Line items
      {
        name: 'line_items_header',
        type: 'text',
        position: { x: 14, y: 88 },
        width: 182,
        height: 7,
        fontSize: 8,
        fontWeight: 'bold',
        fontColor: '#ffffff',
        backgroundColor: '#333333',
      },
      {
        name: 'line_items',
        type: 'text',
        position: { x: 14, y: 96 },
        width: 182,
        height: 120,
        fontSize: 9,
        fontColor: '#333333',
      },
      // Totals
      {
        name: 'subtotal',
        type: 'text',
        position: { x: 140, y: 220 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'total',
        type: 'text',
        position: { x: 140, y: 230 },
        width: 56,
        height: 9,
        fontSize: 12,
        fontWeight: 'bold',
        alignment: 'right',
      },
      // Footer
      {
        name: 'terms',
        type: 'text',
        position: { x: 14, y: 250 },
        width: 182,
        height: 10,
        fontSize: 8,
        fontColor: '#888888',
      },
      {
        name: 'notes',
        type: 'text',
        position: { x: 14, y: 262 },
        width: 182,
        height: 14,
        fontSize: 8,
        fontColor: '#888888',
      },
    ],
  ],
};

// ============================================================================
// Order Confirmation
// ============================================================================
export const orderConfirmationTemplate: Template = {
  basePdf: BLANK_PDF,
  schemas: [
    [
      ...companyHeaderFields,
      {
        name: 'document_title',
        type: 'text',
        position: { x: 120, y: 10 },
        width: 76,
        height: 12,
        fontSize: 18,
        fontWeight: 'bold',
        fontColor: '#1a1a1a',
        alignment: 'right',
      },
      {
        name: 'order_number',
        type: 'text',
        position: { x: 150, y: 24 },
        width: 46,
        height: 8,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'order_date',
        type: 'text',
        position: { x: 150, y: 32 },
        width: 46,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      {
        name: 'ship_via',
        type: 'text',
        position: { x: 150, y: 40 },
        width: 46,
        height: 8,
        fontSize: 9,
        fontColor: '#555555',
        alignment: 'right',
      },
      // Addresses
      ...billToFields,
      ...shipToFields,
      // Line items
      {
        name: 'line_items_header',
        type: 'text',
        position: { x: 14, y: 88 },
        width: 182,
        height: 7,
        fontSize: 8,
        fontWeight: 'bold',
        fontColor: '#ffffff',
        backgroundColor: '#333333',
      },
      {
        name: 'line_items',
        type: 'text',
        position: { x: 14, y: 96 },
        width: 182,
        height: 120,
        fontSize: 9,
        fontColor: '#333333',
      },
      // Totals
      {
        name: 'subtotal',
        type: 'text',
        position: { x: 140, y: 220 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'tax',
        type: 'text',
        position: { x: 140, y: 228 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'shipping',
        type: 'text',
        position: { x: 140, y: 236 },
        width: 56,
        height: 7,
        fontSize: 10,
        alignment: 'right',
      },
      {
        name: 'total',
        type: 'text',
        position: { x: 140, y: 246 },
        width: 56,
        height: 9,
        fontSize: 12,
        fontWeight: 'bold',
        alignment: 'right',
      },
      // Footer
      {
        name: 'terms',
        type: 'text',
        position: { x: 14, y: 262 },
        width: 182,
        height: 10,
        fontSize: 8,
        fontColor: '#888888',
      },
      {
        name: 'notes',
        type: 'text',
        position: { x: 14, y: 272 },
        width: 182,
        height: 10,
        fontSize: 8,
        fontColor: '#888888',
      },
    ],
  ],
};

// ============================================================================
// Registry — lookup by report name
// ============================================================================
export const DEFAULT_TEMPLATES: Record<string, Template> = {
  'Invoice - Standard': invoiceTemplate,
  'Pick Ticket': pickListTemplate,
  'Purchase Order': purchaseOrderTemplate,
  'Order Confirmation': orderConfirmationTemplate,
};

/**
 * Get a default template by report name. Returns undefined if no default exists.
 */
export function getDefaultTemplate(reportName: string): Template | undefined {
  return DEFAULT_TEMPLATES[reportName];
}

/**
 * Get all field names from a template (for mapping UI).
 */
export function getTemplateFieldNames(template: Template): string[] {
  const names: string[] = [];
  for (const page of template.schemas) {
    for (const field of page) {
      if (typeof field === 'object' && 'name' in field) {
        names.push((field as any).name);
      }
    }
  }
  return names;
}
