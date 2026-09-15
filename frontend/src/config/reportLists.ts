/**
 * reportLists.ts — DEPRECATED 2026-08-06
 *
 * Print templates now live in Setting records (purpose='print_template').
 * PrintReportDropdown reads Settings directly.
 *
 * Components still reference this file. Migrate to Setting-based lookup,
 * then delete this file.
 */

export type ReportOutputType = 'print' | 'email' | 'api' | 'json' | 'export' | 'label' | 'merge';
export type ReportCategory = 'report' | 'statement' | 'list' | 'summary' | 'letter' | 'label' | 'export' | 'utility';

export interface ReportDef {
  name: string;
  description: string;
  output_type: ReportOutputType;
  category: ReportCategory;
  sort_order: number;
  role_required?: string;
  security_level?: number;
  wc3_id?: number;
  data?: Record<string, unknown>;
}
