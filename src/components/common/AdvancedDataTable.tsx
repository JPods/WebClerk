/**
 * DEPRECATED — All list pages now import DataGrid directly.
 *
 * If you see a compile error pointing here, change your import to:
 *   import DataGrid from "@/components/common/DataGrid";
 *
 * For the ColumnFilter type, import from ButtonToolbar:
 *   import type { ColumnFilter } from "@/components/common/ButtonToolbar";
 *
 * DataGrid accepts legacy TableColumn-style columns via auto-detection.
 * Pass data={...} and columns={[{name, selector, cell, ...}]} — it works.
 */
export default null;
