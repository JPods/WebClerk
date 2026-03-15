/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// import * as XLSX from 'xlsx';

// export const useExportExcel = (tableData: any[], columns: string[], columnsValue:any[]) => {
//   const worksheet = XLSX.utils.aoa_to_sheet([
//     columns,
//     ...tableData.map((item,index) => [index +1, ...columnsValue.map(column => item[column])])
//   ]);
//   const workbook = XLSX.utils.book_new();
//   XLSX.utils.book_append_sheet(workbook, worksheet, 'Sheet1');
//   XLSX.writeFile(workbook, 'table.xlsx');
// };
