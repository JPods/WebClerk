/**
 * templateService — loads/saves pdfme templates from WC3 Report model.
 *
 * Templates are stored in core.Report records:
 *   - report.config.pdfme_template = the pdfme template JSON
 *   - report.config.field_map = maps WC3 field names to template input names
 *   - report.name = display name
 *   - report.model_name = which transaction type (invoice, order, proposal, etc.)
 *   - report.output_type = "print"
 *
 * Starter templates ship in starter-templates/*.json and are seeded into
 * the Report model on first use.
 */
import apiClient from '@/api/axios';
import type { Template } from '@pdfme/common';

// Bundled starters — imported statically so they're in the build
import invoiceStarter from './starter-templates/invoice.json';
import creditmemoStarter from './starter-templates/creditmemo.json';

export interface PdfmeReportTemplate {
  id?: number;
  name: string;
  description?: string;
  documentType: string;
  template: Template;
  fieldMap?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Starter templates registry
// ---------------------------------------------------------------------------

const STARTERS: Record<string, PdfmeReportTemplate> = {
  'invoice-standard': {
    name: invoiceStarter.name,
    description: invoiceStarter.description,
    documentType: invoiceStarter.documentType,
    template: invoiceStarter.template as unknown as Template,
  },
  'creditmemo-standard': {
    name: creditmemoStarter.name,
    description: creditmemoStarter.description,
    documentType: creditmemoStarter.documentType,
    template: creditmemoStarter.template as unknown as Template,
  },
};

export function getStarterTemplates(): PdfmeReportTemplate[] {
  return Object.values(STARTERS);
}

export function getStarterTemplate(key: string): PdfmeReportTemplate | undefined {
  return STARTERS[key];
}

// ---------------------------------------------------------------------------
// WC3 Report model integration
// ---------------------------------------------------------------------------

/**
 * Load all print templates for a given model (e.g. 'invoice', 'proposal').
 */
export async function loadTemplatesForModel(modelName: string): Promise<PdfmeReportTemplate[]> {
  try {
    const response = await apiClient.get('/wcapi/get/report/', {
      params: {
        filters: JSON.stringify({
          model_name: modelName,
          output_type: 'print',
          is_active: true,
          is_deleted: false,
        }),
        limit: 50,
      },
    });

    const records = response.data?.data || response.data?.records || [];
    return records
      .filter((r: any) => r.config?.pdfme_template)
      .map((r: any) => ({
        id: r.id,
        name: r.name,
        description: r.description || r.purpose || '',
        documentType: r.model_name,
        template: r.config.pdfme_template,
        fieldMap: r.config.field_map,
      }));
  } catch (err) {
    console.warn('Failed to load print templates:', err);
    return [];
  }
}

/**
 * Load a single template by Report id.
 */
export async function loadTemplateById(reportId: number): Promise<PdfmeReportTemplate | null> {
  try {
    const response = await apiClient.get('/wcapi/get/report/', {
      params: { id: reportId },
    });

    const record = response.data?.data || response.data;
    if (!record?.config?.pdfme_template) return null;

    return {
      id: record.id,
      name: record.name,
      description: record.description || record.purpose || '',
      documentType: record.model_name,
      template: record.config.pdfme_template,
      fieldMap: record.config.field_map,
    };
  } catch (err) {
    console.warn('Failed to load template:', err);
    return null;
  }
}

/**
 * Save a template back to the Report model.
 * Creates a new report if no id, updates if id exists.
 */
export async function saveTemplate(tmpl: PdfmeReportTemplate): Promise<PdfmeReportTemplate> {
  const payload: any = {
    model_name: 'report',
    data: {
      name: tmpl.name,
      description: tmpl.description || '',
      model_name: tmpl.documentType,
      output_type: 'print',
      category: 'document',
      config: {
        pdfme_template: tmpl.template,
        field_map: tmpl.fieldMap || {},
      },
    },
  };

  if (tmpl.id) {
    payload.data.id = tmpl.id;
  }

  const response = await apiClient.post('/wcapi/save/', payload);
  const saved = response.data?.data || response.data;

  return {
    ...tmpl,
    id: saved?.id || tmpl.id,
  };
}

/**
 * Delete a template (soft delete via is_active=false).
 */
export async function deleteTemplate(reportId: number): Promise<void> {
  await apiClient.post('/wcapi/save/', {
    model_name: 'report',
    data: { id: reportId, is_active: false },
  });
}

// ---------------------------------------------------------------------------
// Field mapping — maps WC3 transaction data to pdfme input names
// ---------------------------------------------------------------------------

/**
 * Default field map for invoice templates.
 * Keys = pdfme template input names, values = paths into WC3 transaction data.
 */
export const DEFAULT_INVOICE_FIELD_MAP: Record<string, string> = {
  companyName: '_company.name',
  companyDetail: '_company.address_full',
  billTo: '_billTo',
  shipTo: '_shipTo',
  'invoiceInfo.InvoiceNo': 'ida',
  'invoiceInfo.Date': '_dateFormatted',
  'invoiceInfo.Terms': 'terms',
  'invoiceInfo.OrderNo': '_orderNum',
  'metaInfo.Account': 'customer_id',
  'metaInfo.CustPO': '_custPO',
  'metaInfo.SalesID': '_salesId',
  'metaInfo.TypeSale': 'price_level',
  lineItems: '_lines',
  subtotal: 'totals.subtotal',
  tax: 'totals.tax',
  shipping: 'totals.shipping',
  total: 'totals.total',
  balance: 'totals.balance',
  comments: '_comments',
  paymentInfo: '_paymentInfo',
  sellerName: '_company.name',
  sellerAddress: '_company.address_full',
};

/**
 * Build pdfme inputs from a WC3 transaction record + field map.
 */
export function buildInputsFromTransaction(
  data: Record<string, any>,
  fieldMap: Record<string, string>,
  company?: Record<string, any>,
): Record<string, string>[] {
  const inputs: Record<string, string> = {};

  for (const [templateField, dataPath] of Object.entries(fieldMap)) {
    if (dataPath.startsWith('_')) {
      // Computed fields — handled by caller
      continue;
    }
    const value = getNestedValue(data, dataPath);
    if (value !== undefined && value !== null) {
      inputs[templateField] = String(value);
    }
  }

  return [inputs];
}

function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((acc, key) => acc?.[key], obj);
}
