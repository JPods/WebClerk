/**
 * reportLists.ts — Report/print definitions per model (r25 source of truth)
 *
 * Each model has an array of report definitions describing what can be
 * printed, emailed, exported, posted, merged, or labeled from that model's
 * list or detail page.
 *
 * Reports are synced to wc3 Report model records via:
 *   python manage.py sync_reports
 *
 * wc3 counterpart:
 *   common/sync_wcreact/reports.py → REPORT_DEFS
 *   apps/core/models/report.py     → Report model
 *
 * Output types:
 *   print  — PDF / rendered output
 *   email  — Send via SMTP
 *   api    — POST to external endpoint (shippers, DMS, etc.)
 *   json   — Return structured JSON data
 *   export — CSV / Excel file download
 *   label  — Label / barcode printing
 *   merge  — Word / spreadsheet mail merge
 *
 * Categories:
 *   report    — Standard report
 *   statement — Account statement
 *   list      — List / directory
 *   summary   — Summary view
 *   letter    — Letter / email template
 *   label     — Labels / barcodes
 *   export    — Data export
 *   utility   — Utility / script
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReportOutputType = 'print' | 'email' | 'api' | 'json' | 'export' | 'label' | 'merge';
export type ReportCategory = 'report' | 'statement' | 'list' | 'summary' | 'letter' | 'label' | 'export' | 'utility';

export interface ReportDef {
  /** Unique name within the model — stable identifier */
  name: string;
  /** Human-readable description for the menu */
  description: string;
  /** What the report produces */
  output_type: ReportOutputType;
  /** Menu grouping */
  category: ReportCategory;
  /** Display order within the model's report menu */
  sort_order: number;
  /** Role required to see/run (empty = all users) */
  role_required?: string;
  /** Security level — 0 = unrestricted, higher = more restricted */
  security_level?: number;
  /** wc3 Report record id (populated after sync) */
  wc3_id?: number;
  /** Extended config — endpoint URL, template path, parameters, etc. */
  data?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Report definitions per model
// ---------------------------------------------------------------------------

export const MODEL_REPORTS: Record<string, ReportDef[]> = {

  // =========================================================================
  // CUSTOMER  (wc2: QACustomers + customerreports.json)
  // =========================================================================
  customer: [
    // -- print --
    { name: 'Call List, Traveling', description: 'Traveling call list', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'Aged Receivable Report', description: 'Aged receivable report by customer', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Customers by Rep', description: 'Customer list grouped by sales rep', output_type: 'print', category: 'list', sort_order: 30 },
    { name: 'SalesYTD, LastYear, Receivables', description: 'Sales YTD, last year totals, and receivables', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Sales Calc, YTD, LastYear', description: 'Calculated sales comparison YTD vs last year', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Sales LY/Sales YTD by Rep', description: 'Last year vs YTD sales by rep', output_type: 'print', category: 'report', sort_order: 60 },
    { name: 'Contacts In Call List', description: 'Contacts included in call list', output_type: 'print', category: 'list', sort_order: 70 },
    { name: 'Statement', description: 'Customer account statement', output_type: 'print', category: 'statement', sort_order: 80 },
    { name: 'SalesYTD with ProductSummary', description: 'YTD sales with product breakdown', output_type: 'print', category: 'report', sort_order: 90 },
    { name: 'Receivable Summary', description: 'Summary of outstanding receivables', output_type: 'print', category: 'summary', sort_order: 100 },
    { name: 'Condition Report', description: 'Print condition report (QA)', output_type: 'print', category: 'report', sort_order: 110 },
    // -- email --
    { name: 'Email Statement', description: 'Email customer statement via SMTP', output_type: 'email', category: 'statement', sort_order: 200 },
    { name: 'All listed Email', description: 'Email all listed/selected customers', output_type: 'email', category: 'letter', sort_order: 210 },
    { name: 'Warranty Email on Print', description: 'Send warranty email triggered by print', output_type: 'email', category: 'letter', sort_order: 220 },
    // -- label --
    { name: 'iLabels Customer', description: 'Print customer mailing labels', output_type: 'label', category: 'label', sort_order: 300 },
    // -- export --
    { name: 'Customer Export', description: 'Export customer list to CSV', output_type: 'export', category: 'export', sort_order: 400 },
    // -- merge --
    { name: 'Customer Mail Merge', description: 'Merge customer data into Word template', output_type: 'merge', category: 'letter', sort_order: 500 },
    // -- json --
    { name: 'Customer JSON', description: 'Return customer data as structured JSON', output_type: 'json', category: 'export', sort_order: 600 },
  ],

  // =========================================================================
  // ORDER  (wc2: Orders — ~18 reports)
  // =========================================================================
  order: [
    // -- print --
    { name: 'Order Confirmation', description: 'Print order confirmation', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Pick Ticket', description: 'Warehouse pick ticket / pick list', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Packing Slip', description: 'Packing slip for shipment', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Work Order Sheet', description: 'Work order / job sheet generated from order', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Embroidery Worksheet', description: 'Embroidery / customization worksheet', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Schedule A', description: 'Schedule A document for order', output_type: 'print', category: 'report', sort_order: 60 },
    { name: 'Bill of Lading', description: 'Bill of lading for freight shipment', output_type: 'print', category: 'report', sort_order: 70 },
    { name: 'Repair Order', description: 'Repair / service order form', output_type: 'print', category: 'report', sort_order: 80 },
    { name: 'Order - Two Address', description: 'Order form with primary + ship-to addresses', output_type: 'print', category: 'report', sort_order: 90 },
    { name: 'Work Order Confirmation', description: 'Work order confirmation from order', output_type: 'print', category: 'report', sort_order: 100 },
    { name: 'Order Summary', description: 'Order selection summary', output_type: 'print', category: 'summary', sort_order: 110 },
    { name: 'Daily Backlog Report', description: 'Daily open-order backlog report', output_type: 'print', category: 'report', sort_order: 120 },
    { name: 'List of Orders Report', description: 'List report of selected orders', output_type: 'print', category: 'list', sort_order: 130 },
    { name: 'Ad Source Report', description: 'Order ad-source analysis', output_type: 'print', category: 'report', sort_order: 140 },
    { name: 'Show Vendor', description: 'Print vendor info linked to order', output_type: 'print', category: 'report', sort_order: 150 },
    // -- email --
    { name: 'Email Order Confirmation', description: 'Email order confirmation to customer', output_type: 'email', category: 'letter', sort_order: 200 },
    { name: 'Email Condition Report', description: 'Email condition/repair report to customer', output_type: 'email', category: 'letter', sort_order: 210 },
    { name: 'Email Printable Order', description: 'Email printable order document', output_type: 'email', category: 'letter', sort_order: 220 },
    // -- api --
    { name: 'Post to UPS', description: 'POST order to UPS shipping API', output_type: 'api', category: 'utility', sort_order: 300 },
    { name: 'Post Out Orders', description: 'POST order data to external system', output_type: 'api', category: 'utility', sort_order: 310 },
    { name: 'DMS Send Orders', description: 'Send orders to dealer management system', output_type: 'api', category: 'utility', sort_order: 320 },
    { name: 'DMS Bring Orders In', description: 'Import orders from dealer management system', output_type: 'api', category: 'utility', sort_order: 330 },
    // -- export --
    { name: 'Order Export', description: 'Export orders to CSV', output_type: 'export', category: 'export', sort_order: 400 },
    { name: 'Order Web Print', description: 'Web-printable order export', output_type: 'export', category: 'export', sort_order: 410 },
    // -- merge --
    { name: 'Order Mail Merge', description: 'Merge order data into Word template', output_type: 'merge', category: 'letter', sort_order: 500 },
    // -- json --
    { name: 'Order JSON', description: 'Return order data as structured JSON', output_type: 'json', category: 'export', sort_order: 600 },
  ],

  // =========================================================================
  // ORDER LINE  (wc2: OrderLines)
  // =========================================================================
  order_line: [
    { name: 'Open Order Lines', description: 'List of open/unfilled order lines', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'Order Lines Export', description: 'Export order lines to CSV', output_type: 'export', category: 'export', sort_order: 100 },
  ],

  // =========================================================================
  // INVOICE  (wc2: Invoices — ~40 reports)
  // =========================================================================
  invoice: [
    // -- print (standard forms) --
    { name: 'Invoice - Standard', description: 'Standard invoice', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Invoice - Shipping', description: 'Invoice with shipping details', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Invoice - Shipping w/Disc', description: 'Shipping invoice with discount', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Invoice - Bill of Lading', description: 'Invoice bill of lading', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Invoice - PP Ship', description: 'Prepaid shipping invoice', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Invoice - PP Standard', description: 'Prepaid standard invoice', output_type: 'print', category: 'report', sort_order: 60 },
    { name: 'Invoice - Foreign', description: 'Foreign / international invoice', output_type: 'print', category: 'report', sort_order: 70 },
    { name: 'Net Invoice', description: 'Net invoice (no tax / shipping)', output_type: 'print', category: 'report', sort_order: 80 },
    { name: 'Credit Memo', description: 'Credit memo / return document', output_type: 'print', category: 'report', sort_order: 90 },
    { name: 'Invoice Bill of Lading', description: 'Bill of lading from invoice', output_type: 'print', category: 'report', sort_order: 100 },
    { name: 'Packing List with Load Items', description: 'Packing list with loaded item detail', output_type: 'print', category: 'report', sort_order: 110 },
    // -- print (summary / analysis) --
    { name: 'Invoice Paid By', description: 'Payment detail by invoice', output_type: 'print', category: 'report', sort_order: 120 },
    { name: 'Invoice Summary', description: 'Invoice selection summary', output_type: 'print', category: 'summary', sort_order: 130 },
    { name: 'Daily Sales Report', description: 'Daily sales total report', output_type: 'print', category: 'report', sort_order: 140 },
    { name: 'Sales by State', description: 'Sales breakdown by state', output_type: 'print', category: 'report', sort_order: 150 },
    { name: 'Sales by State (Summary)', description: 'Summarized sales by state', output_type: 'print', category: 'summary', sort_order: 160 },
    { name: 'Summary of Sales by Rep', description: 'Sales summary by sales rep', output_type: 'print', category: 'summary', sort_order: 170 },
    { name: 'Rep - Sales/Comm Earned', description: 'Rep sales and commissions earned', output_type: 'print', category: 'report', sort_order: 180 },
    { name: 'Rep (Ind) - Sales/Comm Earned', description: 'Individual rep sales/commission', output_type: 'print', category: 'report', sort_order: 190 },
    { name: 'Broker Commission Report', description: 'Broker commission calculation report', output_type: 'print', category: 'report', sort_order: 200, role_required: 'admin' },
    { name: 'PPC Itemized Sales x Rep', description: 'Itemized sales by rep', output_type: 'print', category: 'report', sort_order: 210 },
    { name: 'PPC Sales x Salesman', description: 'Sales by salesman', output_type: 'print', category: 'report', sort_order: 220 },
    { name: 'PPC Sales x Tax Authority', description: 'Sales by tax authority', output_type: 'print', category: 'report', sort_order: 230 },
    { name: 'PPC MTD Sales', description: 'Month-to-date sales report', output_type: 'print', category: 'report', sort_order: 240 },
    { name: 'PPC Daily Sales', description: 'Daily sales detail', output_type: 'print', category: 'report', sort_order: 250 },
    { name: 'PPC Invoice Charged', description: 'Invoice charge detail', output_type: 'print', category: 'report', sort_order: 260 },
    { name: 'PPC Credit Memo Charge', description: 'Credit memo charge detail', output_type: 'print', category: 'report', sort_order: 270 },
    { name: 'PPC Credit Memo', description: 'Credit memo report', output_type: 'print', category: 'report', sort_order: 280 },
    { name: 'PeopleSoft Draft Billing', description: 'PeopleSoft draft billing output', output_type: 'print', category: 'report', sort_order: 290 },
    { name: 'Sales Tax Report', description: 'Tax breakdown by jurisdiction', output_type: 'print', category: 'report', sort_order: 300, role_required: 'admin' },
    // -- email --
    { name: 'Email Invoice', description: 'Email invoice to customer', output_type: 'email', category: 'letter', sort_order: 400 },
    { name: 'Direct All Invoices', description: 'Batch email all selected invoices', output_type: 'email', category: 'utility', sort_order: 410 },
    // -- label --
    { name: 'iLabel Printing', description: 'Print shipping labels for invoice', output_type: 'label', category: 'label', sort_order: 500 },
    { name: 'iLabel Printing (Meteor)', description: 'Print shipping labels (Meteor format)', output_type: 'label', category: 'label', sort_order: 510 },
    // -- api --
    { name: 'Post to UPS', description: 'POST invoice to UPS for tracking', output_type: 'api', category: 'utility', sort_order: 600 },
    { name: 'Post to UPS Tracking', description: 'Post tracking number to UPS API', output_type: 'api', category: 'utility', sort_order: 610 },
    // -- export --
    { name: 'Invoice Export', description: 'Export invoices to CSV', output_type: 'export', category: 'export', sort_order: 700 },
    { name: 'UPS Export', description: 'Export UPS tracking data', output_type: 'export', category: 'export', sort_order: 710 },
    { name: 'OrdNum UPS Export Track', description: 'Export order-number to UPS tracking map', output_type: 'export', category: 'export', sort_order: 720 },
    { name: 'UPS Order# Export', description: 'Export UPS order numbers', output_type: 'export', category: 'export', sort_order: 730 },
    // -- merge --
    { name: 'Invoice Mail Merge', description: 'Merge invoice data into Word template', output_type: 'merge', category: 'letter', sort_order: 800 },
    // -- json --
    { name: 'Invoice JSON', description: 'Return invoice data as structured JSON', output_type: 'json', category: 'export', sort_order: 900 },
  ],

  // =========================================================================
  // INVOICE LINE  (wc2: InvoiceLines)
  // =========================================================================
  invoice_line: [
    { name: 'Sales By Item and TypeSale', description: 'Sales broken out by item and sale type', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Period Sales Tax Report', description: 'Sales tax report for period', output_type: 'print', category: 'report', sort_order: 20, role_required: 'admin' },
    { name: 'Sales Tax Detail', description: 'Detailed sales tax by line', output_type: 'print', category: 'report', sort_order: 30, role_required: 'admin' },
    { name: 'Invoice Lines Export', description: 'Export invoice lines to CSV', output_type: 'export', category: 'export', sort_order: 100 },
  ],

  // =========================================================================
  // PROPOSAL  (wc2: Proposals — 8 reports)
  // =========================================================================
  proposal: [
    // -- print --
    { name: 'Proposal 1', description: 'Proposal format 1 (standard)', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Proposal 2', description: 'Proposal format 2', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Proposal 3', description: 'Proposal format 3', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Proposal 4', description: 'Proposal format 4', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Customer Quote Form', description: 'Customer-facing quote form', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Proposal Checklist', description: 'Proposal preparation checklist', output_type: 'print', category: 'utility', sort_order: 60 },
    { name: 'Proposal Summary', description: 'Proposal selection summary', output_type: 'print', category: 'summary', sort_order: 70 },
    // -- email --
    { name: 'Email Proposal Basic w/ Q&A', description: 'Email proposal with question/answer section', output_type: 'email', category: 'letter', sort_order: 200 },
    // -- api --
    { name: 'Post Out Proposal', description: 'POST proposal to external system', output_type: 'api', category: 'utility', sort_order: 300 },
    // -- merge --
    { name: 'Post to Word', description: 'Merge proposal into Word document', output_type: 'merge', category: 'letter', sort_order: 400 },
    // -- export --
    { name: 'Proposal Export', description: 'Export proposals to CSV', output_type: 'export', category: 'export', sort_order: 500 },
    // -- json --
    { name: 'Proposal JSON', description: 'Return proposal data as structured JSON', output_type: 'json', category: 'export', sort_order: 600 },
  ],

  // =========================================================================
  // PURCHASE ORDER  (wc2: POs)
  // =========================================================================
  purchase: [
    { name: 'Purchase Order', description: 'Print purchase order (single with line detail)', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Receiving Report', description: 'Print receiving report', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Purchase Summary', description: 'Purchase selection summary', output_type: 'print', category: 'summary', sort_order: 30 },
    { name: 'Email Purchase Order', description: 'Email PO to vendor', output_type: 'email', category: 'letter', sort_order: 200 },
    { name: 'Purchase Export', description: 'Export purchase orders to CSV', output_type: 'export', category: 'export', sort_order: 400 },
    { name: 'Purchase JSON', description: 'Return PO data as structured JSON', output_type: 'json', category: 'export', sort_order: 500 },
  ],

  // =========================================================================
  // ITEM / PRODUCT  (wc2: Items — ~12 reports)
  // =========================================================================
  item: [
    // -- print --
    { name: 'Price List', description: 'Product price list', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'Inventory Status', description: 'Current inventory status by item', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Inventory Report', description: 'Current inventory levels', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Items - Sales by Month', description: 'Item sales broken out by month', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Inventory with Qty Sold', description: 'Inventory showing quantity sold', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Inventory Value', description: 'Inventory valuation report', output_type: 'print', category: 'report', sort_order: 60, role_required: 'admin' },
    { name: 'End of Period Inventory', description: 'End-of-period inventory snapshot', output_type: 'print', category: 'report', sort_order: 70, role_required: 'admin' },
    { name: 'Cushion Inventory', description: 'Cushion-specific inventory report', output_type: 'print', category: 'report', sort_order: 80 },
    { name: 'PPC Inventory Status', description: 'PPC inventory status report', output_type: 'print', category: 'report', sort_order: 90 },
    { name: 'PPC Items w/Qty Sold', description: 'PPC items with quantity sold', output_type: 'print', category: 'report', sort_order: 100 },
    { name: 'Dept Items w/Descriptions', description: 'Items by department with descriptions', output_type: 'print', category: 'list', sort_order: 110 },
    { name: 'Item Listing w/Descriptions', description: 'Full item listing with descriptions', output_type: 'print', category: 'list', sort_order: 120 },
    // -- label --
    { name: 'Item Labels / Barcodes', description: 'Print product labels / barcodes', output_type: 'label', category: 'label', sort_order: 200 },
    // -- export --
    { name: 'Item Export', description: 'Export items to CSV', output_type: 'export', category: 'export', sort_order: 400 },
    // -- merge --
    { name: 'Item Spreadsheet Merge', description: 'Merge item data into spreadsheet template', output_type: 'merge', category: 'export', sort_order: 500 },
    // -- json --
    { name: 'Item JSON', description: 'Return item data as structured JSON', output_type: 'json', category: 'export', sort_order: 600 },
  ],

  // =========================================================================
  // INVENTORY  (wc2: dInventory + InventoryStacks)
  // =========================================================================
  inventory: [
    { name: 'Inventory in Period', description: 'Inventory transactions in period', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'MTD Sales by Stock Number', description: 'Month-to-date sales by stock number', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'MTD Sales by Department', description: 'Month-to-date sales by department', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Goods Receipts', description: 'Goods receipt / receiving log', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Period Report', description: 'Inventory stacks period report', output_type: 'print', category: 'report', sort_order: 50 },
    { name: 'Inventory Export', description: 'Export inventory transactions to CSV', output_type: 'export', category: 'export', sort_order: 100 },
  ],

  // =========================================================================
  // VENDOR  (wc2: Vendors)
  // =========================================================================
  vendor: [
    { name: 'Vendor Contact List', description: 'Active vendor list with contacts', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'AP Aging', description: 'Accounts payable aging report', output_type: 'print', category: 'report', sort_order: 20, role_required: 'admin' },
    { name: 'Vendor Labels', description: 'Print vendor mailing labels', output_type: 'label', category: 'label', sort_order: 100 },
    { name: 'Vendor Export', description: 'Export vendor list to CSV', output_type: 'export', category: 'export', sort_order: 200 },
    { name: 'Vendor JSON', description: 'Return vendor data as structured JSON', output_type: 'json', category: 'export', sort_order: 300 },
  ],

  // =========================================================================
  // CONTACT
  // =========================================================================
  contact: [
    { name: 'Contact List', description: 'Contact directory', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'Contact Labels', description: 'Print contact mailing labels', output_type: 'label', category: 'label', sort_order: 100 },
    { name: 'Contact Export', description: 'Export contacts to CSV', output_type: 'export', category: 'export', sort_order: 200 },
    { name: 'Contact Mail Merge', description: 'Merge contact data into Word template', output_type: 'merge', category: 'letter', sort_order: 300 },
  ],

  // =========================================================================
  // EMPLOYEE  (wc2: Employees)
  // =========================================================================
  employee: [
    { name: 'Employee Listing', description: 'Employee directory listing', output_type: 'print', category: 'list', sort_order: 10, role_required: 'admin' },
    { name: 'Employee Labels', description: 'Print employee mailing labels', output_type: 'label', category: 'label', sort_order: 100, role_required: 'admin' },
    { name: 'Employee Export', description: 'Export employee data to CSV', output_type: 'export', category: 'export', sort_order: 200, role_required: 'admin' },
  ],

  // =========================================================================
  // PAYMENT  (wc2: Payments)
  // =========================================================================
  payment: [
    { name: 'Period Payments Report', description: 'Payment transactions for period', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Bank Deposit', description: 'Bank deposit report / slip', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Cash Drawer Reconciliation', description: 'Cash drawer reconciliation report', output_type: 'print', category: 'report', sort_order: 30, role_required: 'admin' },
    { name: 'Payment Export', description: 'Export payments to CSV', output_type: 'export', category: 'export', sort_order: 100 },
  ],

  // =========================================================================
  // WORK ORDER  (wc2: WorkOrders — 4 reports)
  // =========================================================================
  workorder: [
    { name: 'Work Order', description: 'Print work order form', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'WO Form (based on Order)', description: 'Work order form generated from order data', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Install Scheduler', description: 'Installation scheduling report', output_type: 'print', category: 'report', sort_order: 30 },
    { name: 'Work Order Scheduler', description: 'Work order scheduling report', output_type: 'print', category: 'report', sort_order: 40 },
    { name: 'Inventory Transfer WO', description: 'Inventory transfer work order (auto-generated)', output_type: 'print', category: 'utility', sort_order: 50 },
    { name: 'Job Cost Report', description: 'Job cost breakdown', output_type: 'print', category: 'report', sort_order: 60 },
    { name: 'Work Order Summary', description: 'Work order selection summary', output_type: 'print', category: 'summary', sort_order: 70 },
    { name: 'Work Order Export', description: 'Export work orders to CSV', output_type: 'export', category: 'export', sort_order: 200 },
  ],

  // =========================================================================
  // SERVICE / ACTION  (wc2: Service)
  // =========================================================================
  action: [
    { name: 'Action Report', description: 'Service/action history report', output_type: 'print', category: 'report', sort_order: 10 },
    { name: 'Publisher Report', description: 'Publisher-formatted service report', output_type: 'print', category: 'report', sort_order: 20 },
    { name: 'Email Service Comments', description: 'Email service comments to customer', output_type: 'email', category: 'letter', sort_order: 100 },
    { name: 'Send Mail (Service)', description: 'Send service mail notification', output_type: 'email', category: 'letter', sort_order: 110 },
    { name: 'Action Export', description: 'Export service records to CSV', output_type: 'export', category: 'export', sort_order: 200 },
  ],

  // =========================================================================
  // TAX JURISDICTION  (wc2: Taxes)
  // =========================================================================
  tax_jurisdiction: [
    { name: 'Tax Authority Listing', description: 'Tax authority / jurisdiction listing', output_type: 'print', category: 'list', sort_order: 10 },
    { name: 'Tax Export', description: 'Export tax jurisdictions to CSV', output_type: 'export', category: 'export', sort_order: 100 },
  ],
};

// ---------------------------------------------------------------------------
// Lookup helpers
// ---------------------------------------------------------------------------

/** Get all reports defined for a model key */
export function getReportsForModel(modelKey: string): ReportDef[] {
  return MODEL_REPORTS[modelKey] ?? [];
}

/** Get reports for a model filtered by output type */
export function getReportsByOutputType(modelKey: string, outputType: ReportOutputType): ReportDef[] {
  return getReportsForModel(modelKey).filter((r) => r.output_type === outputType);
}

/** Get reports for a model filtered by category */
export function getReportsByCategory(modelKey: string, category: ReportCategory): ReportDef[] {
  return getReportsForModel(modelKey).filter((r) => r.category === category);
}

/** Get reports visible to a given role (or all if no role restriction) */
export function getReportsForRole(modelKey: string, userRole?: string): ReportDef[] {
  return getReportsForModel(modelKey).filter((r) => {
    if (!r.role_required) return true;
    return userRole === r.role_required || userRole === 'admin';
  });
}

/** Get all model keys that have reports defined */
export function modelKeysWithReports(): string[] {
  return Object.keys(MODEL_REPORTS);
}

/** Get a specific report by model + name */
export function getReportByName(modelKey: string, name: string): ReportDef | undefined {
  return getReportsForModel(modelKey).find((r) => r.name === name);
}
