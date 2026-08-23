export {
  generateTransactionPdf,
  generateStatementPdf,
  downloadTransactionPdf,
  downloadStatementPdf,
  generateTransactionPdfBlob,
} from './generateCommercePdf';
export type { CommercePdfData } from './generateCommercePdf';

export {
  getStarterTemplates,
  getStarterTemplate,
  loadTemplatesForModel,
  loadTemplateById,
  saveTemplate,
  deleteTemplate,
  buildInputsFromTransaction,
  DEFAULT_INVOICE_FIELD_MAP,
} from './templateService';
export type { PdfmeReportTemplate } from './templateService';

export {
  getFieldsForModel,
  getAllFieldsFlat,
  getFieldGroups,
} from './fieldRegistry';
export type { FieldDef } from './fieldRegistry';
