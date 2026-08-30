"""
Data Migration: Load Default B2B GL Accounts
=============================================

Account number format: TYPE-NAME-000
  - TYPE   : ASSET, LIAB, EQUITY, REV, COGS, EXP, CONTRA
  - NAME   : Short readable descriptor (no spaces)
  - 000    : Tail for sub-accounts / divisions (000 = base/default)

To use a sub-account, copy the base account and increment the tail:
  e.g.  REV-SALES-000  (default)
        REV-SALES-001  (division 1)
        REV-SALES-002  (division 2)

Run with:  python manage.py migrate
Reverse:   python manage.py migrate <app> <previous_migration>
"""

from django.db import migrations


# ---------------------------------------------------------------------------
# Account definitions
# Each dict maps directly to GlAccount model fields.
# account_credit / account_debit represent the *typical* double-entry pair
# for that account (what gets posted against it in normal transactions).
# ---------------------------------------------------------------------------

GL_ACCOUNTS = [

    # -----------------------------------------------------------------------
    # ASSETS — Current
    # -----------------------------------------------------------------------
    {
        "account_number": "ASSET-CASH-000",
        "name": "Cash",
        "type": "asset",
        "category": "cash",
        "used_for": "cash",
        "division": 0,
        "comment": "Primary operating cash account.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "ASSET-PETTY-000",
        "name": "Petty Cash",
        "type": "asset",
        "category": "cash",
        "used_for": "cash",
        "division": 0,
        "comment": "Small on-hand cash fund for minor expenses.",
        "account_debit": "ASSET-PETTY-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "ASSET-AR-000",
        "name": "Accounts Receivable",
        "type": "asset",
        "category": "receivables",
        "used_for": "receivables",
        "division": 0,
        "comment": "Amounts owed by customers for goods/services delivered.",
        "account_debit": "ASSET-AR-000",
        "account_credit": "REV-SALES-000",
    },
    {
        "account_number": "ASSET-AROTHER-000",
        "name": "Other Receivables",
        "type": "asset",
        "category": "receivables",
        "used_for": "receivables",
        "division": 0,
        "comment": "Non-trade receivables (employee advances, deposits, etc.).",
        "account_debit": "ASSET-AROTHER-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "ASSET-INVENTORY-000",
        "name": "Inventory",
        "type": "asset",
        "category": "inventory",
        "used_for": "inventory",
        "division": 0,
        "comment": "Goods held for sale or use in production.",
        "account_debit": "ASSET-INVENTORY-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "ASSET-PREPAID-000",
        "name": "Prepaid Expenses",
        "type": "asset",
        "category": "receivables",
        "used_for": None,
        "division": 0,
        "comment": "Expenses paid in advance (insurance, subscriptions, rent).",
        "account_debit": "ASSET-PREPAID-000",
        "account_credit": "ASSET-CASH-000",
    },

    # -----------------------------------------------------------------------
    # ASSETS — Fixed
    # -----------------------------------------------------------------------
    {
        "account_number": "ASSET-EQUIP-000",
        "name": "Equipment",
        "type": "asset",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Machinery, computers, and other equipment.",
        "account_debit": "ASSET-EQUIP-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "ASSET-ACCUMDEPR-000",
        "name": "Accumulated Depreciation",
        "type": "asset",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Contra-asset offsetting fixed asset cost over time.",
        "account_debit": "EXP-DEPRECIATION-000",
        "account_credit": "ASSET-ACCUMDEPR-000",
    },

    # -----------------------------------------------------------------------
    # LIABILITIES — Current
    # -----------------------------------------------------------------------
    {
        "account_number": "LIAB-ACCTSPAY-000",
        "name": "Accounts Payable",
        "type": "liability",
        "category": "payables",
        "used_for": "payables",
        "division": 0,
        "comment": "Amounts owed to vendors/suppliers.",
        "account_debit": "ASSET-INVENTORY-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "LIAB-SALESTAX-000",
        "name": "Sales Tax Payable",
        "type": "liability",
        "category": "payables",
        "used_for": "tax",
        "division": 0,
        "comment": "Sales tax collected from customers, not yet remitted.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-SALESTAX-000",
    },
    {
        "account_number": "LIAB-ACCRUED-000",
        "name": "Accrued Liabilities",
        "type": "liability",
        "category": "payables",
        "used_for": None,
        "division": 0,
        "comment": "Expenses incurred but not yet paid (utilities, wages, etc.).",
        "account_debit": "EXP-GENERAL-000",
        "account_credit": "LIAB-ACCRUED-000",
    },
    {
        "account_number": "LIAB-COMMPAY-000",
        "name": "Commissions Payable",
        "type": "liability",
        "category": "payables",
        "used_for": None,
        "division": 0,
        "comment": "Sales commissions earned but not yet disbursed.",
        "account_debit": "EXP-COMMISSIONS-000",
        "account_credit": "LIAB-COMMPAY-000",
    },
    {
        "account_number": "LIAB-FREIGHTPAY-000",
        "name": "Freight Payable",
        "type": "liability",
        "category": "payables",
        "used_for": None,
        "division": 0,
        "comment": "Freight charges billed to customers, not yet remitted to carrier.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-FREIGHTPAY-000",
    },
    {
        "account_number": "LIAB-DEFREV-000",
        "name": "Deferred Revenue",
        "type": "liability",
        "category": "payables",
        "used_for": None,
        "division": 0,
        "comment": "Customer payments received before goods/services are delivered.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-DEFREV-000",
    },

    # -----------------------------------------------------------------------
    # LIABILITIES — Long-term
    # -----------------------------------------------------------------------
    {
        "account_number": "LIAB-LTNOTES-000",
        "name": "Notes Payable - Long Term",
        "type": "liability",
        "category": "payables",
        "used_for": None,
        "division": 0,
        "comment": "Long-term debt obligations (loans, credit facilities).",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-LTNOTES-000",
    },

    # -----------------------------------------------------------------------
    # EQUITY
    # -----------------------------------------------------------------------
    {
        "account_number": "EQUITY-RETAINED-000",
        "name": "Retained Earnings",
        "type": "equity",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Cumulative net earnings not distributed to owners.",
        "account_debit": None,
        "account_credit": None,
    },
    {
        "account_number": "EQUITY-NETPROFIT-000",
        "name": "Net Profit / Loss",
        "type": "equity",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Current period net income or loss (closed to Retained Earnings at year-end).",
        "account_debit": None,
        "account_credit": None,
    },
    {
        "account_number": "EQUITY-PAID-000",
        "name": "Paid-In Capital",
        "type": "equity",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Capital contributed by owners/shareholders.",
        "account_debit": None,
        "account_credit": None,
    },

    # -----------------------------------------------------------------------
    # REVENUE
    # -----------------------------------------------------------------------
    {
        "account_number": "REV-SALES-000",
        "name": "Sales Revenue",
        "type": "revenue",
        "category": "sales",
        "used_for": "sales",
        "division": 0,
        "comment": "Primary revenue from sale of goods or services.",
        "account_debit": "ASSET-AR-000",
        "account_credit": "REV-SALES-000",
    },
    {
        "account_number": "REV-FREIGHT-000",
        "name": "Freight Revenue",
        "type": "revenue",
        "category": "sales",
        "used_for": "sales",
        "division": 0,
        "comment": "Shipping and handling charges billed to customers.",
        "account_debit": "ASSET-AR-000",
        "account_credit": "REV-FREIGHT-000",
    },
    {
        "account_number": "REV-MISC-000",
        "name": "Miscellaneous Income",
        "type": "revenue",
        "category": "sales",
        "used_for": None,
        "division": 0,
        "comment": "Non-operating or one-off income items.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "REV-MISC-000",
    },
    {
        "account_number": "REV-FINCHARGE-000",
        "name": "Finance Charge Income",
        "type": "revenue",
        "category": "sales",
        "used_for": None,
        "division": 0,
        "comment": "Late payment fees or interest charged to customers.",
        "account_debit": "ASSET-AR-000",
        "account_credit": "REV-FINCHARGE-000",
    },

    # -----------------------------------------------------------------------
    # CONTRA REVENUE
    # -----------------------------------------------------------------------
    {
        "account_number": "CONTRA-RETURNS-000",
        "name": "Sales Returns & Allowances",
        "type": "contra",
        "category": None,
        "used_for": None,
        "division": 0,
        "comment": "Credits issued for returned or defective goods.",
        "account_debit": "CONTRA-RETURNS-000",
        "account_credit": "ASSET-AR-000",
    },
    {
        "account_number": "CONTRA-DISCOUNT-000",
        "name": "Sales Discounts Taken",
        "type": "contra",
        "category": None,
        "used_for": "discounts",
        "division": 0,
        "comment": "Early-payment or volume discounts granted to customers.",
        "account_debit": "CONTRA-DISCOUNT-000",
        "account_credit": "ASSET-AR-000",
    },

    # -----------------------------------------------------------------------
    # COST OF GOODS SOLD
    # -----------------------------------------------------------------------
    {
        "account_number": "COGS-PRODUCTS-000",
        "name": "Cost of Goods Sold",
        "type": "expense",
        "category": "cogs",
        "used_for": "cogs",
        "division": 0,
        "comment": "Direct cost of inventory sold during the period.",
        "account_debit": "COGS-PRODUCTS-000",
        "account_credit": "ASSET-INVENTORY-000",
    },
    {
        "account_number": "COGS-FREIGHT-000",
        "name": "Freight In / Landed Cost",
        "type": "expense",
        "category": "cogs",
        "used_for": "cogs",
        "division": 0,
        "comment": "Inbound shipping and duty costs to acquire inventory.",
        "account_debit": "COGS-FREIGHT-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "COGS-INVTYCLR-000",
        "name": "Inventory Clearing",
        "type": "expense",
        "category": "cogs",
        "used_for": "cogs",
        "division": 0,
        "comment": (
            "Temporary clearing account for purchase receipts pending vendor invoice. "
            "Debited at receipt, credited when AP invoice is posted."
        ),
        "account_debit": "ASSET-INVENTORY-000",
        "account_credit": "COGS-INVTYCLR-000",
    },

    # -----------------------------------------------------------------------
    # OPERATING EXPENSES
    # -----------------------------------------------------------------------
    {
        "account_number": "EXP-COMMISSIONS-000",
        "name": "Commission Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Sales commissions paid to employees or reps.",
        "account_debit": "EXP-COMMISSIONS-000",
        "account_credit": "LIAB-COMMPAY-000",
    },
    {
        "account_number": "EXP-WAGES-000",
        "name": "Wages & Salaries",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Employee compensation excluding commissions.",
        "account_debit": "EXP-WAGES-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-PAYROLLTAX-000",
        "name": "Payroll Tax Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Employer portion of payroll taxes (FICA, FUTA, SUTA).",
        "account_debit": "EXP-PAYROLLTAX-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-RENT-000",
        "name": "Rent Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Office, warehouse, or facility lease payments.",
        "account_debit": "EXP-RENT-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-UTILITIES-000",
        "name": "Utilities Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Electric, gas, water, and internet costs.",
        "account_debit": "EXP-UTILITIES-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-DEPRECIATION-000",
        "name": "Depreciation Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Periodic allocation of fixed asset cost.",
        "account_debit": "EXP-DEPRECIATION-000",
        "account_credit": "ASSET-ACCUMDEPR-000",
    },
    {
        "account_number": "EXP-BADDEBT-000",
        "name": "Bad Debt Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Estimated uncollectable receivables written off.",
        "account_debit": "EXP-BADDEBT-000",
        "account_credit": "ASSET-AR-000",
    },
    {
        "account_number": "EXP-MARKETING-000",
        "name": "Marketing & Advertising",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Advertising, trade shows, and promotional spend.",
        "account_debit": "EXP-MARKETING-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-TRAVEL-000",
        "name": "Travel & Entertainment",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Business travel, meals, and client entertainment.",
        "account_debit": "EXP-TRAVEL-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-INSURANCE-000",
        "name": "Insurance Expense",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "General liability, property, and other business insurance.",
        "account_debit": "EXP-INSURANCE-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-BANKFEES-000",
        "name": "Bank & Processing Fees",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Bank service charges, credit card processing fees, wire fees.",
        "account_debit": "EXP-BANKFEES-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "EXP-GENERAL-000",
        "name": "General & Administrative",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Catch-all for overhead expenses not covered by other accounts.",
        "account_debit": "EXP-GENERAL-000",
        "account_credit": "ASSET-CASH-000",
    },
]


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def load_gl_accounts(apps, schema_editor):
    GlAccount = apps.get_model("accounts", "GlAccount")
    objs = [GlAccount(**data) for data in GL_ACCOUNTS]
    GlAccount.objects.bulk_create(objs, ignore_conflicts=True)


def unload_gl_accounts(apps, schema_editor):
    GlAccount = apps.get_model("accounts", "GlAccount")
    numbers = [d["account_number"] for d in GL_ACCOUNTS]
    GlAccount.objects.filter(account_number__in=numbers).delete()


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------

class Migration(migrations.Migration):

    # !! Update this to match your app name and the real previous migration !!
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            load_gl_accounts,
            reverse_code=unload_gl_accounts,
        ),
    ]
