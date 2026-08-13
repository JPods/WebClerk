/**
 * PanelTable — backward-compatible wrapper around DbColumns.
 *
 * All new code should import DbColumns directly.
 * This file exists so existing imports don't break during migration.
 */
export { DbColumns as PanelTable } from './DbColumns';
export type { DbColumnDef as PanelColumnDef, DbColumnsProps as PanelTableProps } from './DbColumns';
