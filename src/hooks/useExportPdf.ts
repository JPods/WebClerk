/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// import jsPDF from 'jspdf';
// import 'jspdf-autotable';
// import autoTable from 'jspdf-autotable';

// export const useExportPDF = (tableData: any[], columns: string[], columnsValue:any[]) => {
//   const doc = new jsPDF();
//   autoTable(doc, {
//     head: [columns],
//     body: tableData.map((item,index) => [index + 1, ...columnsValue.map(column => item[column])]),
//   })
//   doc.save('table.pdf');
// };