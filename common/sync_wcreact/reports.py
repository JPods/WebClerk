"""
common.sync_wcreact.reports — Canonical report definitions and sync logic.

Defines the master list of reports/print options per model and provides
functions to create/update wc3 Report model records to match.

Used by:
    python manage.py sync_reports

r25 counterpart:
    src/config/reportLists.ts  → MODEL_REPORTS, getReportsForModel()

Legacy source:
    4D UserReport table — reports were per-table with creator type and authLevel.
    readmes/junkdrawer/customerreports.json — sample customer report names.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical report definitions — organized by model_name
#
# Each report dict has:
#   name          (str)  — unique within model, stable identifier
#   description   (str)  — human-readable label for the menu
#   output_type   (str)  — print | email | api | json | export | label
#   category      (str)  — report | statement | list | summary | letter | label | export | utility
#   sort_order    (int)  — display order within model's report menu
#   role_required (str)  — role needed to see/run (blank = all users)
#   security_level(int)  — 0 = unrestricted, higher = more restricted
#   purpose       (str)  — optional grouping tag
#   data          (dict) — extended config (template, endpoint_url, parameters, etc.)
#
# When adding a new report:
#   1. Add the dict below under the correct model key
#   2. Run: python manage.py sync_reports
#   3. Add the matching entry to r25 reportLists.ts
# ---------------------------------------------------------------------------

REPORT_DEFS: dict[str, list[dict]] = {

    # ===================================================================
    # CUSTOMER reports  (wc2: QACustomers table + customerreports.json)
    # ===================================================================
    "customer": [
        # -- print --
        {"name": "Call List, Traveling",            "description": "Traveling call list",                           "output_type": "print", "category": "list",      "sort_order": 10},
        {"name": "Aged Receivable Report",          "description": "Aged receivable report by customer",            "output_type": "print", "category": "report",    "sort_order": 20},
        {"name": "Customers by Rep",                "description": "Customer list grouped by sales rep",            "output_type": "print", "category": "list",      "sort_order": 30},
        {"name": "SalesYTD, LastYear, Receivables", "description": "Sales YTD, last year totals, and receivables",  "output_type": "print", "category": "report",    "sort_order": 40},
        {"name": "Sales Calc, YTD, LastYear",       "description": "Calculated sales comparison YTD vs last year",  "output_type": "print", "category": "report",    "sort_order": 50},
        {"name": "Sales LY/Sales YTD by Rep",       "description": "Last year vs YTD sales by rep",                 "output_type": "print", "category": "report",    "sort_order": 60},
        {"name": "Contacts In Call List",            "description": "Contacts included in call list",               "output_type": "print", "category": "list",      "sort_order": 70},
        {"name": "Statement",                       "description": "Customer account statement",                    "output_type": "print", "category": "statement", "sort_order": 80},
        {"name": "SalesYTD with ProductSummary",    "description": "YTD sales with product breakdown",              "output_type": "print", "category": "report",    "sort_order": 90},
        {"name": "Receivable Summary",              "description": "Summary of outstanding receivables",            "output_type": "print", "category": "summary",   "sort_order": 100},
        {"name": "Condition Report",                "description": "Print condition report (QA)",                   "output_type": "print", "category": "report",    "sort_order": 110},  # wc2: Print Condition Report QA
        # -- email --
        {"name": "Email Statement",                 "description": "Email customer statement via SMTP",             "output_type": "email", "category": "statement", "sort_order": 200},
        {"name": "All listed Email",                "description": "Email all listed/selected customers",           "output_type": "email", "category": "letter",    "sort_order": 210},
        {"name": "Warranty Email on Print",         "description": "Send warranty email triggered by print",        "output_type": "email", "category": "letter",    "sort_order": 220},
        # -- label --
        {"name": "iLabels Customer",                "description": "Print customer mailing labels",                 "output_type": "label", "category": "label",     "sort_order": 300},
        # -- export --
        {"name": "Customer Export",                 "description": "Export customer list to CSV",                    "output_type": "export", "category": "export",   "sort_order": 400},
        # -- merge --
        {"name": "Customer Mail Merge",             "description": "Merge customer data into Word template",        "output_type": "merge", "category": "letter",    "sort_order": 500},
        # -- json / api --
        {"name": "Customer JSON",                   "description": "Return customer data as structured JSON",       "output_type": "json",  "category": "export",   "sort_order": 600},
    ],

    # ===================================================================
    # ORDER reports  (wc2: Orders table — ~18 reports)
    # ===================================================================
    "order": [
        # -- print --
        {"name": "Order Confirmation",              "description": "Print order confirmation",                      "output_type": "print", "category": "report",    "sort_order": 10},
        {"name": "Pick Ticket",                     "description": "Warehouse pick ticket / pick list",             "output_type": "print", "category": "report",    "sort_order": 20},   # wc2: 01_Order - PickList
        {"name": "Packing Slip",                    "description": "Packing slip for shipment",                     "output_type": "print", "category": "report",    "sort_order": 30},
        {"name": "Work Order Sheet",                "description": "Work order / job sheet generated from order",   "output_type": "print", "category": "report",    "sort_order": 40},   # wc2: Work Order
        {"name": "Embroidery Worksheet",            "description": "Embroidery / customization worksheet",          "output_type": "print", "category": "report",    "sort_order": 50},   # wc2: Embroidery Worksheet
        {"name": "Schedule A",                      "description": "Schedule A document for order",                 "output_type": "print", "category": "report",    "sort_order": 60},   # wc2: Schedule A
        {"name": "Bill of Lading",                  "description": "Bill of lading for freight shipment",           "output_type": "print", "category": "report",    "sort_order": 70},   # wc2: BILL OF LADING vessco
        {"name": "Repair Order",                    "description": "Repair / service order form",                   "output_type": "print", "category": "report",    "sort_order": 80},   # wc2: RepairOrder
        {"name": "Order - Two Address",             "description": "Order form with primary + ship-to addresses",   "output_type": "print", "category": "report",    "sort_order": 90},   # wc2: PPC Laser Order, Two Add Loop
        {"name": "Work Order Confirmation",         "description": "Work order confirmation from order",            "output_type": "print", "category": "report",    "sort_order": 100},  # wc2: Work Order Confirmation vessco
        {"name": "Order Summary",                   "description": "Order selection summary",                       "output_type": "print", "category": "summary",   "sort_order": 110},
        {"name": "Daily Backlog Report",            "description": "Daily open-order backlog report",               "output_type": "print", "category": "report",    "sort_order": 120},  # wc2: Daily Backlog Report
        {"name": "List of Orders Report",           "description": "List report of selected orders",                "output_type": "print", "category": "list",      "sort_order": 130},  # wc2: List of Orders Report
        {"name": "Ad Source Report",                "description": "Order ad-source analysis",                      "output_type": "print", "category": "report",    "sort_order": 140},  # wc2: AdSource_Final
        {"name": "Show Vendor",                     "description": "Print vendor info linked to order",             "output_type": "print", "category": "report",    "sort_order": 150},  # wc2: Show Vendor
        # -- email --
        {"name": "Email Order Confirmation",        "description": "Email order confirmation to customer",          "output_type": "email", "category": "letter",    "sort_order": 200},  # wc2: Email Order Option2
        {"name": "Email Condition Report",          "description": "Email condition/repair report to customer",     "output_type": "email", "category": "letter",    "sort_order": 210},  # wc2: Email Condition Report
        {"name": "Email Printable Order",           "description": "Email printable order document",                "output_type": "email", "category": "letter",    "sort_order": 220},  # wc2: emailPrintableOrder
        # -- api  (posting to shippers / external systems) --
        {"name": "Post to UPS",                     "description": "POST order to UPS shipping API",                "output_type": "api",   "category": "utility",   "sort_order": 300},  # wc2: 001 Post to UPS
        {"name": "Post Out Orders",                 "description": "POST order data to external system",            "output_type": "api",   "category": "utility",   "sort_order": 310},  # wc2: Post Out Orders
        {"name": "DMS Send Orders",                 "description": "Send orders to dealer management system",       "output_type": "api",   "category": "utility",   "sort_order": 320},  # wc2: DMS Send Orders
        {"name": "DMS Bring Orders In",             "description": "Import orders from dealer management system",   "output_type": "api",   "category": "utility",   "sort_order": 330},  # wc2: DMS Bring Orders In
        # -- export --
        {"name": "Order Export",                    "description": "Export orders to CSV",                          "output_type": "export", "category": "export",   "sort_order": 400},
        {"name": "Order Web Print",                 "description": "Web-printable order export",                    "output_type": "export", "category": "export",   "sort_order": 410},  # wc2: OrderWebPrint
        # -- merge --
        {"name": "Order Mail Merge",                "description": "Merge order data into Word template",           "output_type": "merge", "category": "letter",    "sort_order": 500},
        # -- json --
        {"name": "Order JSON",                      "description": "Return order data as structured JSON",          "output_type": "json",  "category": "export",   "sort_order": 600},
    ],

    # ===================================================================
    # ORDER LINE reports  (wc2: OrderLines table)
    # ===================================================================
    "order_line": [
        {"name": "Open Order Lines",                "description": "List of open/unfilled order lines",             "output_type": "print",  "category": "list",    "sort_order": 10},   # wc2: Open Order Lines
        {"name": "Order Lines Export",              "description": "Export order lines to CSV",                      "output_type": "export", "category": "export",  "sort_order": 100},
    ],

    # ===================================================================
    # INVOICE reports  (wc2: Invoices table — ~40 reports)
    # ===================================================================
    "invoice": [
        # -- print (standard forms) --
        {"name": "Invoice - Standard",              "description": "Standard invoice",                              "output_type": "print", "category": "report",    "sort_order": 10},   # wc2: Invoice 1 - Standard
        {"name": "Invoice - Shipping",              "description": "Invoice with shipping details",                 "output_type": "print", "category": "report",    "sort_order": 20},   # wc2: Invoice 2 - Shipping
        {"name": "Invoice - Shipping w/Disc",       "description": "Shipping invoice with discount",                "output_type": "print", "category": "report",    "sort_order": 30},   # wc2: Invoice 3 - Shipping w/disc
        {"name": "Invoice - Bill of Lading",        "description": "Invoice bill of lading",                        "output_type": "print", "category": "report",    "sort_order": 40},   # wc2: Invoice 5 - Bill of Lading
        {"name": "Invoice - PP Ship",               "description": "Prepaid shipping invoice",                      "output_type": "print", "category": "report",    "sort_order": 50},   # wc2: Invoice 6 - PP Ship
        {"name": "Invoice - PP Standard",           "description": "Prepaid standard invoice",                      "output_type": "print", "category": "report",    "sort_order": 60},   # wc2: Invoice 7 - PP Std
        {"name": "Invoice - Foreign",               "description": "Foreign / international invoice",               "output_type": "print", "category": "report",    "sort_order": 70},   # wc2: Invoice 1 - Foriegn [sic]
        {"name": "Net Invoice",                     "description": "Net invoice (no tax / shipping)",               "output_type": "print", "category": "report",    "sort_order": 80},   # wc2: Net Invoice
        {"name": "Credit Memo",                     "description": "Credit memo / return document",                 "output_type": "print", "category": "report",    "sort_order": 90},   # wc2: CREDIT-MEMO
        {"name": "Invoice Bill of Lading",          "description": "Bill of lading from invoice",                   "output_type": "print", "category": "report",    "sort_order": 100},  # wc2: Invoice Bill of Lading vessco
        {"name": "Packing List with Load Items",    "description": "Packing list with loaded item detail",          "output_type": "print", "category": "report",    "sort_order": 110},  # wc2: PK_PacingList with Load Items
        # -- print (summary / analysis) --
        {"name": "Invoice Paid By",                 "description": "Payment detail by invoice",                     "output_type": "print", "category": "report",    "sort_order": 120},  # wc2: Invoice Paid By
        {"name": "Invoice Summary",                 "description": "Invoice selection summary",                     "output_type": "print", "category": "summary",   "sort_order": 130},
        {"name": "Daily Sales Report",              "description": "Daily sales total report",                      "output_type": "print", "category": "report",    "sort_order": 140},  # wc2: Daily Sales Report
        {"name": "Sales by State",                  "description": "Sales breakdown by state",                      "output_type": "print", "category": "report",    "sort_order": 150},  # wc2: Sales by State
        {"name": "Sales by State (Summary)",        "description": "Summarized sales by state",                     "output_type": "print", "category": "summary",   "sort_order": 160},  # wc2: Sales by State (Summary)
        {"name": "Summary of Sales by Rep",         "description": "Sales summary by sales rep",                    "output_type": "print", "category": "summary",   "sort_order": 170},  # wc2: Summary of Sales by Rep
        {"name": "Rep - Sales/Comm Earned",         "description": "Rep sales and commissions earned",              "output_type": "print", "category": "report",    "sort_order": 180},  # wc2: Rep - Sales/Comm earned
        {"name": "Rep (Ind) - Sales/Comm Earned",   "description": "Individual rep sales/commission",               "output_type": "print", "category": "report",    "sort_order": 190},  # wc2: Rep (ind)- Sales/Comm earned
        {"name": "Broker Commission Report",        "description": "Broker commission calculation report",          "output_type": "print", "category": "report",    "sort_order": 200,  "role_required": "admin"},  # wc2: Broker Commission Report
        {"name": "PPC Itemized Sales x Rep",        "description": "Itemized sales by rep",                         "output_type": "print", "category": "report",    "sort_order": 210},  # wc2: PPC Itemized Sales x Rep
        {"name": "PPC Sales x Salesman",            "description": "Sales by salesman",                             "output_type": "print", "category": "report",    "sort_order": 220},  # wc2: PPC Sales x Salesman
        {"name": "PPC Sales x Tax Authority",       "description": "Sales by tax authority",                        "output_type": "print", "category": "report",    "sort_order": 230},  # wc2: PPC Sales x Tax Authority
        {"name": "PPC MTD Sales",                   "description": "Month-to-date sales report",                    "output_type": "print", "category": "report",    "sort_order": 240},  # wc2: PPC MTD Sales
        {"name": "PPC Daily Sales",                 "description": "Daily sales detail",                            "output_type": "print", "category": "report",    "sort_order": 250},  # wc2: PPC Daily Sales
        {"name": "PPC Invoice Charged",             "description": "Invoice charge detail",                         "output_type": "print", "category": "report",    "sort_order": 260},  # wc2: PPC Invoice Charged
        {"name": "PPC Credit Memo Charge",          "description": "Credit memo charge detail",                     "output_type": "print", "category": "report",    "sort_order": 270},  # wc2: PPC Credit Memo Charge
        {"name": "PPC Credit Memo",                 "description": "Credit memo report",                            "output_type": "print", "category": "report",    "sort_order": 280},  # wc2: PPC Credit Memo
        {"name": "PeopleSoft Draft Billing",        "description": "PeopleSoft draft billing output",               "output_type": "print", "category": "report",    "sort_order": 290},  # wc2: PeopleSoft Draft Billing
        {"name": "Sales Tax Report",                "description": "Tax breakdown by jurisdiction",                  "output_type": "print", "category": "report",    "sort_order": 300,  "role_required": "admin"},
        # -- email --
        {"name": "Email Invoice",                   "description": "Email invoice to customer",                     "output_type": "email", "category": "letter",    "sort_order": 400},  # wc2: Email Invoice
        {"name": "Direct All Invoices",             "description": "Batch email all selected invoices",             "output_type": "email", "category": "utility",   "sort_order": 410},  # wc2: Direct All Invoices
        # -- label --
        {"name": "iLabel Printing",                 "description": "Print shipping labels for invoice",             "output_type": "label", "category": "label",     "sort_order": 500},  # wc2: iLabel Printing2
        {"name": "iLabel Printing (Meteor)",        "description": "Print shipping labels (Meteor format)",         "output_type": "label", "category": "label",     "sort_order": 510},  # wc2: iLabel Printing_Meteor
        # -- api  (posting to shippers / external verification) --
        {"name": "Post to UPS",                     "description": "POST invoice to UPS for tracking",              "output_type": "api",   "category": "utility",   "sort_order": 600},  # wc2: 01_Post to UPS
        {"name": "Post to UPS Tracking",            "description": "Post tracking number to UPS API",               "output_type": "api",   "category": "utility",   "sort_order": 610},  # wc2: Post to UPS Tracking
        # -- export --
        {"name": "Invoice Export",                  "description": "Export invoices to CSV",                         "output_type": "export", "category": "export",   "sort_order": 700},
        {"name": "UPS Export",                      "description": "Export UPS tracking data",                       "output_type": "export", "category": "export",   "sort_order": 710},  # wc2: UPS EXPORT
        {"name": "OrdNum UPS Export Track",         "description": "Export order-number to UPS tracking map",        "output_type": "export", "category": "export",   "sort_order": 720},  # wc2: OrdNum_UPS_Export_Track
        {"name": "UPS Order# Export",               "description": "Export UPS order numbers",                       "output_type": "export", "category": "export",   "sort_order": 730},  # wc2: !!UPS Order# Export
        # -- merge --
        {"name": "Invoice Mail Merge",              "description": "Merge invoice data into Word template",          "output_type": "merge", "category": "letter",   "sort_order": 800},
        # -- json --
        {"name": "Invoice JSON",                    "description": "Return invoice data as structured JSON",         "output_type": "json",  "category": "export",   "sort_order": 900},
    ],

    # ===================================================================
    # INVOICE LINE reports  (wc2: InvoiceLines table)
    # ===================================================================
    "invoice_line": [
        {"name": "Sales By Item and TypeSale",      "description": "Sales broken out by item and sale type",         "output_type": "print",  "category": "report",  "sort_order": 10},   # wc2
        {"name": "Period Sales Tax Report",         "description": "Sales tax report for period",                    "output_type": "print",  "category": "report",  "sort_order": 20,  "role_required": "admin"},  # wc2
        {"name": "Sales Tax Detail",                "description": "Detailed sales tax by line",                     "output_type": "print",  "category": "report",  "sort_order": 30,  "role_required": "admin"},  # wc2: Sales Tax + Sales Tax QR
        {"name": "Invoice Lines Export",            "description": "Export invoice lines to CSV",                    "output_type": "export", "category": "export",  "sort_order": 100},
    ],

    # ===================================================================
    # PROPOSAL reports  (wc2: Proposals table — 8 reports)
    # ===================================================================
    "proposal": [
        # -- print (multiple formats) --
        {"name": "Proposal 1",                      "description": "Proposal format 1 (standard)",                   "output_type": "print", "category": "report",    "sort_order": 10},   # wc2: Proposal 1
        {"name": "Proposal 2",                      "description": "Proposal format 2",                              "output_type": "print", "category": "report",    "sort_order": 20},   # wc2: Proposal 2
        {"name": "Proposal 3",                      "description": "Proposal format 3",                              "output_type": "print", "category": "report",    "sort_order": 30},   # wc2: Proposal 3
        {"name": "Proposal 4",                      "description": "Proposal format 4",                              "output_type": "print", "category": "report",    "sort_order": 40},   # wc2: Proposal 4
        {"name": "Customer Quote Form",             "description": "Customer-facing quote form",                     "output_type": "print", "category": "report",    "sort_order": 50},   # wc2: !Customer Quote Form
        {"name": "Proposal Checklist",              "description": "Proposal preparation checklist",                 "output_type": "print", "category": "utility",   "sort_order": 60},   # wc2: SR[Ppl]Proposal CheckList
        {"name": "Proposal Summary",                "description": "Proposal selection summary",                     "output_type": "print", "category": "summary",   "sort_order": 70},
        # -- email --
        {"name": "Email Proposal Basic w/ Q&A",     "description": "Email proposal with question/answer section",    "output_type": "email", "category": "letter",    "sort_order": 200},  # wc2: Email Proposal Basic w/ Q&A
        # -- api --
        {"name": "Post Out Proposal",               "description": "POST proposal to external system",               "output_type": "api",   "category": "utility",   "sort_order": 300},  # wc2: PostOutProposal
        # -- merge --
        {"name": "Post to Word",                    "description": "Merge proposal into Word document",              "output_type": "merge", "category": "letter",    "sort_order": 400},  # wc2: Post to Word
        # -- export --
        {"name": "Proposal Export",                 "description": "Export proposals to CSV",                         "output_type": "export", "category": "export",   "sort_order": 500},
        # -- json --
        {"name": "Proposal JSON",                   "description": "Return proposal data as structured JSON",        "output_type": "json",  "category": "export",   "sort_order": 600},
    ],

    # ===================================================================
    # PURCHASE ORDER reports  (wc2: POs table)
    # ===================================================================
    "purchase": [
        {"name": "Purchase Order",                  "description": "Print purchase order (single with line detail)",  "output_type": "print", "category": "report",    "sort_order": 10},   # wc2: PO SingleLoop w/ InventoryStacks
        {"name": "Receiving Report",                "description": "Print receiving report",                          "output_type": "print", "category": "report",    "sort_order": 20},
        {"name": "Purchase Summary",                "description": "Purchase selection summary",                      "output_type": "print", "category": "summary",   "sort_order": 30},
        {"name": "Email Purchase Order",            "description": "Email PO to vendor",                              "output_type": "email", "category": "letter",    "sort_order": 200},  # wc2: Email PO
        {"name": "Purchase Export",                 "description": "Export purchase orders to CSV",                    "output_type": "export", "category": "export",   "sort_order": 400},
        {"name": "Purchase JSON",                   "description": "Return PO data as structured JSON",               "output_type": "json",  "category": "export",   "sort_order": 500},
    ],

    # ===================================================================
    # ITEM / PRODUCT reports  (wc2: Items table — ~12 reports)
    # ===================================================================
    "item": [
        # -- print --
        {"name": "Price List",                      "description": "Product price list",                              "output_type": "print", "category": "list",      "sort_order": 10},
        {"name": "Inventory Status",                "description": "Current inventory status by item",                "output_type": "print", "category": "report",    "sort_order": 20},   # wc2: Inventory Status
        {"name": "Inventory Report",                "description": "Current inventory levels",                        "output_type": "print", "category": "report",    "sort_order": 30},   # wc2: Inventory Report
        {"name": "Items - Sales by Month",          "description": "Item sales broken out by month",                  "output_type": "print", "category": "report",    "sort_order": 40},   # wc2: Items - Sales by month
        {"name": "Inventory with Qty Sold",         "description": "Inventory showing quantity sold",                 "output_type": "print", "category": "report",    "sort_order": 50},   # wc2: Inventory with Quantity Sold.4qr
        {"name": "Inventory Value",                 "description": "Inventory valuation report",                      "output_type": "print", "category": "report",    "sort_order": 60,  "role_required": "admin"},  # wc2: PPC Inventory Value
        {"name": "End of Period Inventory",         "description": "End-of-period inventory snapshot",                "output_type": "print", "category": "report",    "sort_order": 70,  "role_required": "admin"},  # wc2: PPC End of Period Inventory
        {"name": "Cushion Inventory",               "description": "Cushion-specific inventory report",               "output_type": "print", "category": "report",    "sort_order": 80},   # wc2: PPC Cushion Inventory
        {"name": "PPC Inventory Status",            "description": "PPC inventory status report",                     "output_type": "print", "category": "report",    "sort_order": 90},   # wc2: PPC Inventory Status
        {"name": "PPC Items w/Qty Sold",            "description": "PPC items with quantity sold",                    "output_type": "print", "category": "report",    "sort_order": 100},  # wc2: PPC Items w/Qty Sold
        {"name": "Dept Items w/Descriptions",       "description": "Items by department with descriptions",           "output_type": "print", "category": "list",      "sort_order": 110},  # wc2: Dept Items w/Descriptions
        {"name": "Item Listing w/Descriptions",     "description": "Full item listing with descriptions",             "output_type": "print", "category": "list",      "sort_order": 120},  # wc2: Item listing w/Descriptions
        # -- label --
        {"name": "Item Labels / Barcodes",          "description": "Print product labels / barcodes",                 "output_type": "label", "category": "label",     "sort_order": 200},  # wc2: Build Barcodes_Ver_04
        # -- export --
        {"name": "Item Export",                     "description": "Export items to CSV",                              "output_type": "export", "category": "export",   "sort_order": 400},
        # -- merge --
        {"name": "Item Spreadsheet Merge",          "description": "Merge item data into spreadsheet template",        "output_type": "merge", "category": "export",   "sort_order": 500},
        # -- json --
        {"name": "Item JSON",                       "description": "Return item data as structured JSON",              "output_type": "json",  "category": "export",   "sort_order": 600},
    ],

    # ===================================================================
    # INVENTORY reports  (wc2: dInventory + InventoryStacks tables)
    # ===================================================================
    "inventory": [
        {"name": "Inventory in Period",             "description": "Inventory transactions in period",                "output_type": "print",  "category": "report",  "sort_order": 10},   # wc2: dInventory in Period
        {"name": "MTD Sales by Stock Number",       "description": "Month-to-date sales by stock number",             "output_type": "print",  "category": "report",  "sort_order": 20},   # wc2: MTD Sales by Stock Number
        {"name": "MTD Sales by Department",         "description": "Month-to-date sales by department",               "output_type": "print",  "category": "report",  "sort_order": 30},   # wc2: MTD Sales by Department
        {"name": "Goods Receipts",                  "description": "Goods receipt / receiving log",                    "output_type": "print",  "category": "report",  "sort_order": 40},   # wc2: Goods Receipts (InventoryStacks)
        {"name": "Period Report",                   "description": "Inventory stacks period report",                  "output_type": "print",  "category": "report",  "sort_order": 50},   # wc2: Period Report (InventoryStacks)
        {"name": "Inventory Export",                "description": "Export inventory transactions to CSV",             "output_type": "export", "category": "export",  "sort_order": 100},
    ],

    # ===================================================================
    # VENDOR reports  (wc2: Vendors table)
    # ===================================================================
    "vendor": [
        {"name": "Vendor Contact List",             "description": "Active vendor list with contacts",                "output_type": "print",  "category": "list",    "sort_order": 10},   # wc2: SR[Vendors] Contact List
        {"name": "AP Aging",                        "description": "Accounts payable aging report",                   "output_type": "print",  "category": "report",  "sort_order": 20,  "role_required": "admin"},
        {"name": "Vendor Labels",                   "description": "Print vendor mailing labels",                     "output_type": "label",  "category": "label",   "sort_order": 100},
        {"name": "Vendor Export",                   "description": "Export vendor list to CSV",                        "output_type": "export", "category": "export",  "sort_order": 200},
        {"name": "Vendor JSON",                     "description": "Return vendor data as structured JSON",            "output_type": "json",   "category": "export",  "sort_order": 300},
    ],

    # ===================================================================
    # CONTACT reports
    # ===================================================================
    "contact": [
        {"name": "Contact List",                    "description": "Contact directory",                                "output_type": "print",  "category": "list",    "sort_order": 10},
        {"name": "Contact Labels",                  "description": "Print contact mailing labels",                     "output_type": "label",  "category": "label",   "sort_order": 100},
        {"name": "Contact Export",                  "description": "Export contacts to CSV",                            "output_type": "export", "category": "export",  "sort_order": 200},
        {"name": "Contact Mail Merge",              "description": "Merge contact data into Word template",            "output_type": "merge",  "category": "letter",  "sort_order": 300},
    ],

    # ===================================================================
    # EMPLOYEE reports  (wc2: Employees table)
    # ===================================================================
    "employee": [
        {"name": "Employee Listing",                "description": "Employee directory listing",                       "output_type": "print",  "category": "list",    "sort_order": 10,  "role_required": "admin"},  # wc2: Employee Listing
        {"name": "Employee Labels",                 "description": "Print employee mailing labels",                    "output_type": "label",  "category": "label",   "sort_order": 100, "role_required": "admin"},
        {"name": "Employee Export",                 "description": "Export employee data to CSV",                       "output_type": "export", "category": "export",  "sort_order": 200, "role_required": "admin"},
    ],

    # ===================================================================
    # PAYMENT reports  (wc2: Payments table)
    # ===================================================================
    "payment": [
        {"name": "Period Payments Report",          "description": "Payment transactions for period",                  "output_type": "print",  "category": "report",  "sort_order": 10},   # wc2: Period Payments Report
        {"name": "Bank Deposit",                    "description": "Bank deposit report / slip",                        "output_type": "print",  "category": "report",  "sort_order": 20},   # wc2: Bank Deposit
        {"name": "Cash Drawer Reconciliation",      "description": "Cash drawer reconciliation report",                "output_type": "print",  "category": "report",  "sort_order": 30,  "role_required": "admin"},  # wc2: PPC Cash Drawer Reconciliation
        {"name": "Payment Export",                  "description": "Export payments to CSV",                            "output_type": "export", "category": "export",  "sort_order": 100},
    ],

    # ===================================================================
    # WORK ORDER reports  (wc2: WorkOrders table — 4 reports)
    # ===================================================================
    "workorder": [
        {"name": "Work Order",                      "description": "Print work order form",                            "output_type": "print",  "category": "report",  "sort_order": 10},
        {"name": "WO Form (based on Order)",        "description": "Work order form generated from order data",        "output_type": "print",  "category": "report",  "sort_order": 20},   # wc2: WO Form (based on Order)
        {"name": "Install Scheduler",               "description": "Installation scheduling report",                   "output_type": "print",  "category": "report",  "sort_order": 30},   # wc2: 01_Install Scheduler
        {"name": "Work Order Scheduler",            "description": "Work order scheduling report",                     "output_type": "print",  "category": "report",  "sort_order": 40},   # wc2: SR[WorkOrders] Scheduler
        {"name": "Inventory Transfer WO",           "description": "Inventory transfer work order (auto-generated)",   "output_type": "print",  "category": "utility", "sort_order": 50},   # wc2: InventoryTransferWO_Auto
        {"name": "Job Cost Report",                 "description": "Job cost breakdown",                               "output_type": "print",  "category": "report",  "sort_order": 60},
        {"name": "Work Order Summary",              "description": "Work order selection summary",                     "output_type": "print",  "category": "summary", "sort_order": 70},
        {"name": "Work Order Export",               "description": "Export work orders to CSV",                         "output_type": "export", "category": "export",  "sort_order": 200},
    ],

    # ===================================================================
    # SERVICE / ACTION reports  (wc2: Service table)
    # ===================================================================
    "action": [
        {"name": "Action Report",                   "description": "Service/action history report",                    "output_type": "print",  "category": "report",  "sort_order": 10},   # wc2: Action Report
        {"name": "Publisher Report",                 "description": "Publisher-formatted service report",               "output_type": "print",  "category": "report",  "sort_order": 20},   # wc2: Publisher Report
        {"name": "Email Service Comments",          "description": "Email service comments to customer",               "output_type": "email",  "category": "letter",  "sort_order": 100},  # wc2: Email Service Comments
        {"name": "Send Mail (Service)",             "description": "Send service mail notification",                   "output_type": "email",  "category": "letter",  "sort_order": 110},  # wc2: Send Mail
        {"name": "Action Export",                   "description": "Export service records to CSV",                     "output_type": "export", "category": "export",  "sort_order": 200},
    ],

    # ===================================================================
    # TAX JURISDICTION reports  (wc2: Taxes table)
    # ===================================================================
    "tax_jurisdiction": [
        {"name": "Tax Authority Listing",           "description": "Tax authority / jurisdiction listing",              "output_type": "print",  "category": "list",    "sort_order": 10},   # wc2: Tax Authority Listing
        {"name": "Tax Export",                      "description": "Export tax jurisdictions to CSV",                    "output_type": "export", "category": "export",  "sort_order": 100},
    ],
}

# Fields that get set/updated on each report record
SYNC_FIELDS = [
    "description", "output_type", "category", "sort_order",
    "role_required", "security_level", "purpose", "data",
]

# Defaults for fields not specified in a definition dict
_FIELD_DEFAULTS = {
    "description": "",
    "output_type": "print",
    "category": "report",
    "sort_order": 0,
    "role_required": "",
    "security_level": 0,
    "purpose": "",
    "data": {},
}


# ---------------------------------------------------------------------------
# Sync functions (called by management command or programmatically)
# ---------------------------------------------------------------------------

def sync_reports(stdout, style, models=None, dry_run=False):
    """
    Create/update Report records to match REPORT_DEFS. Idempotent.
    Matches on (model_name + name) as the unique key.

    Args:
        stdout:  management command stdout (or sys.stdout)
        style:   management command style helper (for colored output)
        models:  optional list of model keys to sync (None = all)
        dry_run: if True, preview only

    Returns:
        (created, updated, unchanged) counts
    """
    from apps.core.models import Report

    defs_to_sync = REPORT_DEFS
    if models:
        defs_to_sync = {k: v for k, v in REPORT_DEFS.items() if k in models}
        missing = set(models) - set(defs_to_sync.keys())
        if missing:
            stdout.write(style.ERROR(
                f"Unknown model key(s): {', '.join(sorted(missing))}"
            ))
            return 0, 0, 0

    created_count = 0
    updated_count = 0
    unchanged_count = 0

    for model_name, reports in defs_to_sync.items():
        stdout.write(f"\n  {model_name} ({len(reports)} reports):")

        for defn in reports:
            name = defn["name"]
            try:
                report = Report.objects.get(model_name=model_name, name=name)
                changes = []
                for field in SYNC_FIELDS:
                    new_val = defn.get(field, _FIELD_DEFAULTS.get(field))
                    old_val = getattr(report, field)
                    # Normalize None vs empty for comparison
                    if old_val is None and new_val is None:
                        continue
                    if old_val is None and new_val == "":
                        continue
                    if old_val == "" and new_val is None:
                        continue
                    if new_val != old_val:
                        changes.append((field, old_val, new_val))

                if changes:
                    for field, old_val, new_val in changes:
                        setattr(report, field, new_val)
                    if not dry_run:
                        report.save(update_fields=[f for f, _, _ in changes])
                    tag = "[DRY RUN] " if dry_run else ""
                    stdout.write(style.WARNING(
                        f"    {tag}Updated '{name}': "
                        + ", ".join(f"{f}: {o} → {n}" for f, o, n in changes)
                    ))
                    updated_count += 1
                else:
                    stdout.write(f"    Unchanged: '{name}' (id={report.id})")
                    unchanged_count += 1

            except Report.DoesNotExist:
                if not dry_run:
                    report = Report.objects.create(
                        model_name=model_name,
                        name=name,
                        description=defn.get("description", ""),
                        output_type=defn.get("output_type", "print"),
                        category=defn.get("category", "report"),
                        sort_order=defn.get("sort_order", 0),
                        role_required=defn.get("role_required", ""),
                        security_level=defn.get("security_level", 0),
                        purpose=defn.get("purpose", ""),
                        data=defn.get("data", {}),
                    )
                    stdout.write(style.SUCCESS(
                        f"    Created: '{name}' (id={report.id}) [{defn.get('output_type', 'print')}]"
                    ))
                else:
                    stdout.write(style.SUCCESS(
                        f"    [DRY RUN] Would create: '{name}' [{defn.get('output_type', 'print')}]"
                    ))
                created_count += 1

    # Summary
    stdout.write("")
    tag = "[DRY RUN] " if dry_run else ""
    stdout.write(style.SUCCESS(
        f"{tag}Sync complete: "
        f"{created_count} created, {updated_count} updated, "
        f"{unchanged_count} unchanged"
    ))

    return created_count, updated_count, unchanged_count


def list_reports(stdout, models=None):
    """Display all reports currently in the database, grouped by model."""
    from apps.core.models import Report

    qs = Report.objects.filter(is_active=True).order_by("model_name", "sort_order", "name")
    if models:
        qs = qs.filter(model_name__in=models)

    count = qs.count()
    stdout.write(f"Reports in database ({count}):")
    if count == 0:
        stdout.write("  (none — run sync_reports to populate)")
        return

    current_model = None
    for r in qs:
        if r.model_name != current_model:
            current_model = r.model_name
            model_count = qs.filter(model_name=current_model).count()
            stdout.write(f"\n  {current_model} ({model_count}):")
        role = f"  role={r.role_required}" if r.role_required else ""
        stdout.write(
            f"    id={r.id:>3}  {r.name:<35s} "
            f"[{r.output_type or 'print':<6s}] {r.category or 'report':<10s}"
            f" sort={r.sort_order}{role}"
        )


def show_reports_for_r25(stdout, models=None):
    """Output wc3 reports formatted as r25 TypeScript code."""
    from apps.core.models import Report

    qs = Report.objects.filter(is_active=True).order_by("model_name", "sort_order", "name")
    if models:
        qs = qs.filter(model_name__in=models)

    if not qs.exists():
        stdout.write("No report records found in wc3.")
        return

    stdout.write("// Paste into r25 reportLists.ts MODEL_REPORTS:")
    stdout.write("")

    current_model = None
    for r in qs:
        if r.model_name != current_model:
            if current_model is not None:
                stdout.write("  ],")
                stdout.write("")
            current_model = r.model_name
            stdout.write(f"  {current_model}: [")

        role_str = f", role_required: '{r.role_required}'" if r.role_required else ""
        stdout.write(
            f"    {{ name: '{r.name}', description: '{r.description}', "
            f"output_type: '{r.output_type}', category: '{r.category}', "
            f"sort_order: {r.sort_order}{role_str} }},"
        )

    if current_model is not None:
        stdout.write("  ],")
