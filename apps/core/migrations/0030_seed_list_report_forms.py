"""
Seed config.form for list/analysis reports using data_table sections.

These render current db.list records — no separate query.
"""
from django.db import migrations
import json


def list_form(title, model, columns, group_by=None, group_label=None):
    """Build a list report form.json."""
    sections = [
        {"type": "company_header", "logo": True, "show_address": False, "show_contact": False},
        {"type": "meta_row", "fields": [
            {"field": "_report_date", "label": "Report Date", "format": "date"},
        ]},
    ]
    dt = {
        "type": "data_table",
        "columns": columns,
        "grand_totals": True,
    }
    if group_by:
        dt["group_by"] = group_by
        dt["group_label"] = group_label or group_by
        dt["group_subtotals"] = True
    sections.append(dt)
    return {
        "model": model,
        "title": title,
        "paper": "letter",
        "version": 1,
        "sections": sections,
    }


# Column shorthand
def col(field, label, fmt=None, align=None, width=None):
    c = {"field": field, "label": label}
    if fmt: c["format"] = fmt
    if align: c["align"] = align
    if width: c["width"] = width
    return c


# ---------------------------------------------------------------------------
# List form definitions by model
# ---------------------------------------------------------------------------

# -- Customer / Contact lists --
CUSTOMER_LIST_COLS = [
    col("ida", "Account #", width="12%"),
    col("company", "Company", width="25%"),
    col("attention", "Contact", width="20%"),
    col("phone", "Phone", width="15%"),
    col("email", "Email", width="18%"),
]

AGING_COLS = [
    col("ida", "Account #", width="10%"),
    col("company", "Company", width="20%"),
    col("totals.current", "Current", "currency", "right", "12%"),
    col("totals.over30", "30 Days", "currency", "right", "12%"),
    col("totals.over60", "60 Days", "currency", "right", "12%"),
    col("totals.over90", "90+ Days", "currency", "right", "12%"),
    col("totals.balance", "Total", "currency", "right", "12%"),
]

SALES_ANALYSIS_COLS = [
    col("ida", "Account #", width="10%"),
    col("company", "Company", width="20%"),
    col("totals.ytd_sales", "YTD Sales", "currency", "right", "15%"),
    col("totals.ly_sales", "Last Year", "currency", "right", "15%"),
    col("totals.balance", "Balance", "currency", "right", "12%"),
]

# -- Invoice analysis --
INVOICE_LIST_COLS = [
    col("ida", "Invoice #", width="10%"),
    col("company", "Customer", width="20%"),
    col("dt_created", "Date", "date", width="10%"),
    col("status", "Status", width="8%"),
    col("totals.total", "Total", "currency", "right", "12%"),
    col("totals.tax", "Tax", "currency", "right", "10%"),
    col("totals.balance", "Balance", "currency", "right", "12%"),
]

SALES_BY_STATE_COLS = [
    col("ida", "Invoice #", width="10%"),
    col("company", "Customer", width="20%"),
    col("config.ship_to.state", "State", width="8%"),
    col("totals.total", "Total", "currency", "right", "15%"),
    col("totals.tax", "Tax", "currency", "right", "12%"),
]

COMMISSION_COLS = [
    col("ida", "Invoice #", width="10%"),
    col("company", "Customer", width="20%"),
    col("dt_created", "Date", "date", width="10%"),
    col("totals.total", "Sale", "currency", "right", "12%"),
    col("totals.commission", "Commission", "currency", "right", "12%"),
]

# -- Order analysis --
ORDER_LIST_COLS = [
    col("ida", "Order #", width="10%"),
    col("company", "Customer", width="20%"),
    col("dt_created", "Date", "date", width="10%"),
    col("status", "Status", width="8%"),
    col("totals.total", "Total", "currency", "right", "12%"),
    col("totals.balance", "Open", "currency", "right", "12%"),
]

# -- Item / Inventory --
ITEM_LIST_COLS = [
    col("ida", "Item #", width="12%"),
    col("description", "Description", width="30%"),
    col("inventory.on_hand", "On Hand", "number", "right", "10%"),
    col("inventory.committed", "Committed", "number", "right", "10%"),
    col("inventory.available", "Available", "number", "right", "10%"),
    col("price.sell", "Price", "currency", "right", "12%"),
]

PRICE_LIST_COLS = [
    col("ida", "Item #", width="15%"),
    col("description", "Description", width="40%"),
    col("price.sell", "Price", "currency", "right", "15%"),
    col("uom", "UOM", width="10%"),
]

INVENTORY_VALUE_COLS = [
    col("ida", "Item #", width="12%"),
    col("description", "Description", width="25%"),
    col("inventory.on_hand", "On Hand", "number", "right", "10%"),
    col("cost.unit", "Unit Cost", "currency", "right", "12%"),
    col("cost.extended", "Total Value", "currency", "right", "15%"),
]

# -- Vendor --
VENDOR_LIST_COLS = [
    col("ida", "Vendor #", width="12%"),
    col("company", "Company", width="25%"),
    col("attention", "Contact", width="18%"),
    col("phone", "Phone", width="15%"),
    col("email", "Email", width="18%"),
]

# -- GL / Accounting --
GL_JOURNAL_COLS = [
    col("ida", "Entry #", width="10%"),
    col("dt_created", "Date", "date", width="10%"),
    col("account.ida", "Account", width="15%"),
    col("account.name", "Description", width="25%"),
    col("debit", "Debit", "currency", "right", "12%"),
    col("credit", "Credit", "currency", "right", "12%"),
]

# -- Payment --
PAYMENT_LIST_COLS = [
    col("ida", "Payment #", width="10%"),
    col("company", "From", width="20%"),
    col("dt_created", "Date", "date", width="10%"),
    col("config.method", "Method", width="10%"),
    col("total", "Amount", "currency", "right", "15%"),
]

# -- Employee --
EMPLOYEE_LIST_COLS = [
    col("ida", "ID", width="10%"),
    col("attention", "Name", width="25%"),
    col("phone", "Phone", width="15%"),
    col("email", "Email", width="20%"),
]

# -- Rep --
REP_COLS = [
    col("ida", "Rep #", width="10%"),
    col("attention", "Name", width="20%"),
    col("phone", "Phone", width="15%"),
    col("totals.commission", "Commission", "currency", "right", "15%"),
]

# -- Tax --
TAX_LIST_COLS = [
    col("ida", "Code", width="12%"),
    col("name", "Jurisdiction", width="30%"),
    col("config.rate", "Rate", "percent", "right", "12%"),
]

# ---------------------------------------------------------------------------
# Map: (model_name, report_name) → form
# ---------------------------------------------------------------------------

LIST_FORM_ASSIGNMENTS = [
    # Customer
    ("customer", "Call List, Traveling", list_form("Call List", "customer", CUSTOMER_LIST_COLS)),
    ("customer", "Aged Receivable Report", list_form("Aged Receivables", "customer", AGING_COLS)),
    ("customer", "Customers by Rep", list_form("Customers by Rep", "customer", CUSTOMER_LIST_COLS, "sales_rep", "Sales Rep")),
    ("customer", "SalesYTD, LastYear, Receivables", list_form("Sales YTD / Last Year", "customer", SALES_ANALYSIS_COLS)),
    ("customer", "Sales Calc, YTD, LastYear", list_form("Sales Comparison", "customer", SALES_ANALYSIS_COLS)),
    ("customer", "Sales LY/Sales YTD by Rep", list_form("Sales by Rep", "customer", SALES_ANALYSIS_COLS, "sales_rep", "Rep")),
    ("customer", "Contacts In Call List", list_form("Call List Contacts", "customer", CUSTOMER_LIST_COLS)),
    ("customer", "SalesYTD with ProductSummary", list_form("Sales with Product Summary", "customer", SALES_ANALYSIS_COLS)),
    ("customer", "Receivable Summary", list_form("Receivable Summary", "customer", AGING_COLS)),
    ("customer", "Condition Report", list_form("Condition Report", "customer", CUSTOMER_LIST_COLS)),
    ("customer", "Customer Profile", list_form("Customer Profile", "customer", CUSTOMER_LIST_COLS)),
    ("customer", "Aging Report", list_form("Aging Report", "customer", AGING_COLS)),
    ("customer", "Receivables Report", list_form("Receivables", "customer", AGING_COLS)),
    ("customer", "Customer Activity Report", list_form("Customer Activity", "customer", SALES_ANALYSIS_COLS)),
    # Contact
    ("contact", "Contact List", list_form("Contact List", "contact", CUSTOMER_LIST_COLS)),
    ("contact", "Contact Directory", list_form("Contact Directory", "contact", CUSTOMER_LIST_COLS)),
    ("contact", "AR Aging", list_form("AR Aging", "contact", AGING_COLS)),
    ("contact", "AP Aging", list_form("AP Aging", "contact", AGING_COLS)),
    ("contact", "Customer Profitability", list_form("Customer Profitability", "contact", SALES_ANALYSIS_COLS)),
    ("contact", "Overdue Notice", list_form("Overdue Notice", "contact", AGING_COLS)),
    ("contact", "Sales by Customer", list_form("Sales by Customer", "contact", SALES_ANALYSIS_COLS)),
    ("contact", "Sales by Salesperson", list_form("Sales by Salesperson", "contact", SALES_ANALYSIS_COLS, "sales_rep", "Salesperson")),
    # Invoice analysis
    ("invoice", "Invoice Summary", list_form("Invoice Summary", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "Daily Sales Report", list_form("Daily Sales", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "Sales by State", list_form("Sales by State", "invoice", SALES_BY_STATE_COLS, "config.ship_to.state", "State")),
    ("invoice", "Sales by State (Summary)", list_form("Sales by State Summary", "invoice", SALES_BY_STATE_COLS, "config.ship_to.state", "State")),
    ("invoice", "Summary of Sales by Rep", list_form("Sales by Rep", "invoice", INVOICE_LIST_COLS, "sales_rep", "Rep")),
    ("invoice", "Commission Report", list_form("Commission Report", "invoice", COMMISSION_COLS, "sales_rep", "Rep")),
    ("invoice", "Rep - Sales/Comm Earned", list_form("Rep Commission", "invoice", COMMISSION_COLS, "sales_rep", "Rep")),
    ("invoice", "Rep (Ind) - Sales/Comm Earned", list_form("Individual Rep Commission", "invoice", COMMISSION_COLS)),
    ("invoice", "Broker Commission Report", list_form("Broker Commission", "invoice", COMMISSION_COLS)),
    ("invoice", "Invoice Paid By", list_form("Invoice Paid By", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "Past Due Notice", list_form("Past Due Notice", "invoice", AGING_COLS)),
    ("invoice", "Sales Tax Report", list_form("Sales Tax Report", "invoice", SALES_BY_STATE_COLS, "config.tax_juris", "Tax Jurisdiction")),
    ("invoice", "AR Aging Report", list_form("AR Aging", "invoice", AGING_COLS)),
    ("invoice", "Sales by Customer", list_form("Sales by Customer", "invoice", INVOICE_LIST_COLS, "company", "Customer")),
    ("invoice", "Sales by Rep", list_form("Sales by Rep", "invoice", INVOICE_LIST_COLS, "sales_rep", "Rep")),
    ("invoice", "Tax Report", list_form("Tax Report", "invoice", SALES_BY_STATE_COLS, "config.tax_juris", "Jurisdiction")),
    # PPC reports (same structure, different titles)
    ("invoice", "PPC Itemized Sales x Rep", list_form("PPC Itemized Sales by Rep", "invoice", INVOICE_LIST_COLS, "sales_rep", "Rep")),
    ("invoice", "PPC Sales x Salesman", list_form("PPC Sales by Salesman", "invoice", INVOICE_LIST_COLS, "sales_rep", "Salesman")),
    ("invoice", "PPC Sales x Tax Authority", list_form("PPC Sales by Tax Authority", "invoice", SALES_BY_STATE_COLS, "config.tax_juris", "Tax Authority")),
    ("invoice", "PPC MTD Sales", list_form("PPC MTD Sales", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "PPC Daily Sales", list_form("PPC Daily Sales", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "PPC Invoice Charged", list_form("PPC Invoice Charged", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "PPC Credit Memo Charge", list_form("PPC Credit Memo Charge", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "PPC Credit Memo", list_form("PPC Credit Memo", "invoice", INVOICE_LIST_COLS)),
    ("invoice", "PeopleSoft Draft Billing", list_form("PeopleSoft Draft Billing", "invoice", INVOICE_LIST_COLS)),
    # Invoice line
    ("invoice_line", "Sales By Item and TypeSale", list_form("Sales by Item", "invoice_line", [
        col("item.ida_item", "Item #", width="12%"), col("item.description", "Description", width="25%"),
        col("quantity.active", "Qty", "number", "right", "10%"), col("price.extended", "Extended", "currency", "right", "15%"),
    ], "item.type_sale", "Type Sale")),
    ("invoice_line", "Period Sales Tax Report", list_form("Period Sales Tax", "invoice_line", [
        col("item.ida_item", "Item #", width="12%"), col("price.extended", "Amount", "currency", "right", "15%"),
        col("price.tax", "Tax", "currency", "right", "12%"),
    ])),
    ("invoice_line", "Sales Tax Detail", list_form("Sales Tax Detail", "invoice_line", [
        col("item.ida_item", "Item #", width="12%"), col("price.extended", "Amount", "currency", "right", "15%"),
        col("price.tax", "Tax", "currency", "right", "12%"),
    ])),
    # Order analysis
    ("order", "Order Summary", list_form("Order Summary", "order", ORDER_LIST_COLS)),
    ("order", "Daily Backlog Report", list_form("Daily Backlog", "order", ORDER_LIST_COLS)),
    ("order", "List of Orders Report", list_form("Orders List", "order", ORDER_LIST_COLS)),
    ("order", "Ad Source Report", list_form("Ad Source Report", "order", ORDER_LIST_COLS, "source.campaign_name", "Ad Source")),
    ("order", "Show Vendor", list_form("Vendor Orders", "order", ORDER_LIST_COLS)),
    ("order", "Sales Order — Summary", list_form("Sales Order Summary", "order", ORDER_LIST_COLS)),
    ("order", "Customs Proforma", list_form("Customs Proforma", "order", ORDER_LIST_COLS)),
    ("order", "Back Order Report", list_form("Back Orders", "order", ORDER_LIST_COLS)),
    ("order", "Backorder Report", list_form("Backorder Report", "order", ORDER_LIST_COLS)),
    ("order", "Open Orders Report", list_form("Open Orders", "order", ORDER_LIST_COLS)),
    ("order_line", "Open Order Lines", list_form("Open Order Lines", "order_line", [
        col("ida", "Line #", width="8%"), col("item.ida_item", "Item #", width="12%"),
        col("item.description", "Description", width="30%"),
        col("quantity.active", "Ordered", "number", "right", "10%"),
        col("quantity.remaining", "Open", "number", "right", "10%"),
    ])),
    # Item / Inventory
    ("item", "Price List", list_form("Price List", "item", PRICE_LIST_COLS)),
    ("item", "Inventory Status", list_form("Inventory Status", "item", ITEM_LIST_COLS)),
    ("item", "Inventory Report", list_form("Inventory Report", "item", ITEM_LIST_COLS)),
    ("item", "Items - Sales by Month", list_form("Items Sales by Month", "item", ITEM_LIST_COLS)),
    ("item", "Inventory with Qty Sold", list_form("Inventory with Qty Sold", "item", ITEM_LIST_COLS)),
    ("item", "Inventory Value", list_form("Inventory Value", "item", INVENTORY_VALUE_COLS)),
    ("item", "End of Period Inventory", list_form("End of Period Inventory", "item", INVENTORY_VALUE_COLS)),
    ("item", "Cushion Inventory", list_form("Cushion Inventory", "item", ITEM_LIST_COLS)),
    ("item", "PPC Inventory Status", list_form("PPC Inventory Status", "item", ITEM_LIST_COLS)),
    ("item", "PPC Items w/Qty Sold", list_form("PPC Items with Qty Sold", "item", ITEM_LIST_COLS)),
    ("item", "Dept Items w/Descriptions", list_form("Items by Department", "item", ITEM_LIST_COLS, "department", "Department")),
    ("item", "Item Listing w/Descriptions", list_form("Item Listing", "item", ITEM_LIST_COLS)),
    ("item", "Product Spec Sheet", list_form("Product Spec Sheet", "item", ITEM_LIST_COLS)),
    ("item", "Reorder Report", list_form("Reorder Report", "item", ITEM_LIST_COLS)),
    ("item", "Sales by Item", list_form("Sales by Item", "item", ITEM_LIST_COLS)),
    ("item", "Margin Velocity", list_form("Margin Velocity", "item", ITEM_LIST_COLS)),
    ("item", "BOM Expansion", list_form("BOM Expansion", "item", ITEM_LIST_COLS)),
    # Inventory
    ("inventory", "Inventory in Period", list_form("Inventory in Period", "inventory", ITEM_LIST_COLS)),
    ("inventory", "MTD Sales by Stock Number", list_form("MTD Sales by Stock #", "inventory", ITEM_LIST_COLS)),
    ("inventory", "MTD Sales by Department", list_form("MTD Sales by Dept", "inventory", ITEM_LIST_COLS, "department", "Department")),
    ("inventory", "Goods Receipts", list_form("Goods Receipts", "inventory", ITEM_LIST_COLS)),
    ("inventory", "Period Report", list_form("Period Report", "inventory", ITEM_LIST_COLS)),
    ("inventory_layer", "Inventory Count Sheet", list_form("Count Sheet", "inventory_layer", ITEM_LIST_COLS)),
    # Vendor
    ("vendor", "Vendor Contact List", list_form("Vendor Contacts", "vendor", VENDOR_LIST_COLS)),
    ("vendor", "Vendor List", list_form("Vendor List", "vendor", VENDOR_LIST_COLS)),
    ("vendor", "AP Aging", list_form("AP Aging", "vendor", AGING_COLS)),
    ("vendor", "AP Aging Report", list_form("AP Aging", "vendor", AGING_COLS)),
    ("vendor", "Vendor Profile", list_form("Vendor Profile", "vendor", VENDOR_LIST_COLS)),
    ("vendor", "Vendor Statement", list_form("Vendor Statement", "vendor", AGING_COLS)),
    ("vendor", "Vendor Scorecard", list_form("Vendor Scorecard", "vendor", VENDOR_LIST_COLS)),
    # GL / Accounting
    ("gl_account", "Chart of Accounts", list_form("Chart of Accounts", "gl_account", [
        col("ida", "Account #", width="15%"), col("name", "Name", width="35%"),
        col("config.type", "Type", width="15%"), col("config.balance", "Balance", "currency", "right", "15%"),
    ])),
    ("gl_journal", "Journal Entry Report", list_form("Journal Entries", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "Trial Balance", list_form("Trial Balance", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "Journal Listing", list_form("Journal Listing", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "Sales Journal", list_form("Sales Journal", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "Purchase Journal", list_form("Purchase Journal", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "GL Summary", list_form("GL Summary", "gl_journal", GL_JOURNAL_COLS)),
    ("gl_journal", "Cash Receipts Journal", list_form("Cash Receipts", "gl_journal", GL_JOURNAL_COLS)),
    # Ledger
    ("ledger", "AR Aging Summary", list_form("AR Aging Summary", "ledger", AGING_COLS)),
    ("ledger", "AP Aging Summary", list_form("AP Aging Summary", "ledger", AGING_COLS)),
    ("ledger", "Open Receivables", list_form("Open Receivables", "ledger", AGING_COLS)),
    # Payment
    ("payment", "Period Payments Report", list_form("Period Payments", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Bank Deposit", list_form("Bank Deposit", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Deposit Report", list_form("Deposit Report", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Cash Drawer Reconciliation", list_form("Cash Drawer", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Bank Reconciliation", list_form("Bank Reconciliation", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Cash Flow Report", list_form("Cash Flow", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Commission Report", list_form("Commission Report", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Payment Summary", list_form("Payment Summary", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Refund Report", list_form("Refund Report", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Disbursement Report", list_form("Disbursement Report", "payment", PAYMENT_LIST_COLS)),
    ("payment", "Payment Journal", list_form("Payment Journal", "payment", PAYMENT_LIST_COLS)),
    # Employee
    ("employee", "Employee Listing", list_form("Employee Listing", "employee", EMPLOYEE_LIST_COLS)),
    # Rep
    ("rep", "Commission Report", list_form("Commission Report", "rep", REP_COLS)),
    ("rep", "Sales by Rep", list_form("Sales by Rep", "rep", REP_COLS)),
    ("rep", "Rep Activity", list_form("Rep Activity", "rep", REP_COLS)),
    # Tax
    ("tax_jurisdiction", "Tax Authority Listing", list_form("Tax Authorities", "tax_jurisdiction", TAX_LIST_COLS)),
    # Manufacturer
    ("manufacturer", "Sales by Manufacturer", list_form("Sales by Manufacturer", "manufacturer", SALES_ANALYSIS_COLS)),
    ("manufacturer", "Rebate Accrual Report", list_form("Rebate Accrual", "manufacturer", SALES_ANALYSIS_COLS)),
    # Action
    ("action", "Action Report", list_form("Action Report", "action", [
        col("ida", "Action #", width="10%"), col("name", "Subject", width="30%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("action", "Publisher Report", list_form("Publisher Report", "action", [
        col("ida", "Action #", width="10%"), col("name", "Subject", width="30%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("action", "Task List", list_form("Task List", "action", [
        col("ida", "ID", width="8%"), col("name", "Task", width="30%"),
        col("status", "Status", width="10%"), col("priority", "Priority", width="10%"),
        col("dt_created", "Date", "date", width="12%"),
    ])),
    ("action", "Project Status Report", list_form("Project Status", "action", [
        col("ida", "ID", width="8%"), col("name", "Task", width="30%"),
        col("status", "Status", width="10%"), col("priority", "Priority", width="10%"),
    ])),
    # BOM
    ("bill_of_material", "BOM Report", list_form("BOM Report", "bill_of_material", ITEM_LIST_COLS)),
    ("bill_of_material", "Where-Used Report", list_form("Where-Used", "bill_of_material", ITEM_LIST_COLS)),
    # Proposal analysis
    ("proposal", "Proposal Summary", list_form("Proposal Summary", "proposal", [
        col("ida", "Proposal #", width="10%"), col("company", "Customer", width="20%"),
        col("dt_created", "Date", "date", width="10%"), col("status", "Status", width="8%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("proposal", "Proposal Checklist", list_form("Checklist", "proposal", [
        col("ida", "Proposal #", width="10%"), col("company", "Customer", width="25%"),
        col("status", "Status", width="10%"),
    ])),
    ("proposal", "Proposal — Summary", list_form("Proposal Summary", "proposal", [
        col("ida", "Proposal #", width="10%"), col("company", "Customer", width="20%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("proposal", "Quote Follow-up List", list_form("Quote Follow-up", "proposal", [
        col("ida", "Proposal #", width="10%"), col("company", "Customer", width="25%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("proposal", "Quote Conversion Report", list_form("Quote Conversion", "proposal", [
        col("ida", "Proposal #", width="10%"), col("company", "Customer", width="25%"),
        col("status", "Status", width="10%"), col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    # Purchase analysis
    ("purchase", "Purchase Summary", list_form("Purchase Summary", "purchase", [
        col("ida", "PO #", width="10%"), col("company", "Vendor", width="20%"),
        col("dt_created", "Date", "date", width="10%"), col("status", "Status", width="8%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("purchase", "Purchase Order — Summary", list_form("PO Summary", "purchase", [
        col("ida", "PO #", width="10%"), col("company", "Vendor", width="20%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("purchase", "AP Aging Report", list_form("AP Aging", "purchase", AGING_COLS)),
    ("purchase", "PO vs Receipt Variance", list_form("PO vs Receipt Variance", "purchase", [
        col("ida", "PO #", width="10%"), col("company", "Vendor", width="20%"),
        col("totals.total", "PO Total", "currency", "right", "12%"),
    ])),
    ("purchase", "Vendor Scorecard", list_form("Vendor Scorecard", "purchase", VENDOR_LIST_COLS)),
    # Work order analysis
    ("workorder", "Job Cost Report", list_form("Job Cost", "workorder", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("workorder", "Work Order Summary", list_form("WO Summary", "workorder", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("status", "Status", width="10%"), col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("workorder", "Install Scheduler", list_form("Install Schedule", "workorder", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("workorder", "Work Order Scheduler", list_form("WO Schedule", "workorder", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    # Work order (work_order model_name variant)
    ("work_order", "Work Order", list_form("Work Orders", "work_order", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("status", "Status", width="10%"), col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    ("work_order", "Service Report", list_form("Service Reports", "work_order", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("status", "Status", width="10%"),
    ])),
    ("work_order", "Time & Materials Summary", list_form("Time & Materials", "work_order", [
        col("ida", "WO #", width="10%"), col("company", "Customer", width="20%"),
        col("totals.total", "Total", "currency", "right", "12%"),
    ])),
    # Document / misc
    ("document", "Document Index", list_form("Document Index", "document", [
        col("ida", "Doc #", width="10%"), col("name", "Name", width="30%"),
        col("mime_type", "Type", width="15%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("warehouse", "Warehouse Inventory", list_form("Warehouse Inventory", "warehouse", ITEM_LIST_COLS)),
    ("warehouse", "Cycle Count Sheet", list_form("Cycle Count Sheet", "warehouse", ITEM_LIST_COLS)),
    ("serial", "Serial History", list_form("Serial History", "serial", [
        col("ida", "Serial #", width="15%"), col("item.ida_item", "Item #", width="15%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("requisition", "Requisition", list_form("Requisitions", "requisition", [
        col("ida", "Req #", width="10%"), col("status", "Status", width="10%"),
        col("dt_created", "Date", "date", width="12%"),
    ])),
    ("receipt", "Receiving Report", list_form("Receiving Report", "receipt", [
        col("ida", "Receipt #", width="10%"), col("company", "Vendor", width="20%"),
        col("dt_created", "Date", "date", width="10%"),
    ])),
    ("campaign", "Campaign ROI", list_form("Campaign ROI", "campaign", [
        col("ida", "Campaign", width="15%"), col("name", "Name", width="25%"),
        col("config.cost", "Cost", "currency", "right", "12%"),
        col("config.revenue", "Revenue", "currency", "right", "12%"),
    ])),
    ("project", "Project Summary", list_form("Project Summary", "project", [
        col("ida", "Project #", width="10%"), col("name", "Name", width="30%"),
        col("status", "Status", width="10%"), col("dt_created", "Date", "date", width="12%"),
    ])),
    ("question_answer", "Condition Report", list_form("Condition Report", "question_answer", [
        col("ida", "ID", width="8%"), col("name", "Question", width="40%"),
        col("config.answer", "Answer", width="30%"),
    ])),
    ("question_answer", "Inspection Checklist", list_form("Inspection Checklist", "question_answer", [
        col("ida", "ID", width="8%"), col("name", "Item", width="40%"),
        col("config.result", "Result", width="20%"),
    ])),
    ("question_answer", "Q&A Report", list_form("Q&A Report", "question_answer", [
        col("ida", "ID", width="8%"), col("name", "Question", width="40%"),
        col("config.answer", "Answer", width="30%"),
    ])),
]


def seed_list_forms(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    updated = 0
    for model_name, report_name, form in LIST_FORM_ASSIGNMENTS:
        reports = Report.objects.filter(model_name=model_name, name=report_name)
        for report in reports:
            config = report.config if isinstance(report.config, dict) else {}
            if 'form' in config:
                continue  # don't overwrite forms seeded in 0029
            config['form'] = form
            report.config = config
            report.save(update_fields=['config'])
            updated += 1
    print(f"  Updated {updated} Report records with list form.json layouts")


def remove_list_forms(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    for report in Report.objects.filter(output_type='print'):
        config = report.config or {}
        if isinstance(config, dict) and 'form' in config:
            form = config.get('form', {})
            if isinstance(form, dict) and form.get('sections'):
                has_dt = any(s.get('type') == 'data_table' for s in form['sections'])
                if has_dt:
                    del config['form']
                    report.config = config
                    report.save(update_fields=['config'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0029_seed_report_forms'),
    ]
    operations = [
        migrations.RunPython(seed_list_forms, remove_list_forms),
    ]
