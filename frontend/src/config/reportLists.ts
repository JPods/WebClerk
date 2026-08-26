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

/** @deprecated Use Setting records with purpose='print_template' */
export const MODEL_REPORTS: Record<string, ReportDef[]> = {};

/** @deprecated */
export function getReportsForModel(_modelKey: string): ReportDef[] { return []; }
/** @deprecated */
export function getReportsByOutputType(_modelKey: string, _outputType: ReportOutputType): ReportDef[] { return []; }
/** @deprecated */
export function getReportsByCategory(_modelKey: string, _category: ReportCategory): ReportDef[] { return []; }
/** @deprecated */
export function getReportsForRole(_modelKey: string, _userRole?: string): ReportDef[] { return []; }
/** @deprecated */
export function modelKeysWithReports(): string[] { return []; }
/** @deprecated */
export function getReportByName(_modelKey: string, _name: string): ReportDef | undefined { return undefined; }
