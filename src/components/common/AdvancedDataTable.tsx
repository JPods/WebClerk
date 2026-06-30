/**
 * @deprecated Use DataGrid instead.
 *
 * This file re-exports from the deprecated AdvancedDataTable for backward
 * compatibility. Pages should migrate to DataGrid + useListFieldConfig + FieldOrderDialog.
 *
 * Migration: replace <AdvancedDataTable> with <DataGrid> and use useListFieldConfig hook.
 * See CustomerList.tsx for the migration pattern.
 */
export { default, parseSearchTerms } from './AdvancedDataTable_DEPRECATED';
export type { ColumnFilter, AdvancedDataTableProps, AdvancedDataTableHandle } from './AdvancedDataTable_DEPRECATED';
