"""
Data migration: assign new 4-digit ida values to GL accounts and
update gl_journals.account references to match.
"""
from django.db import migrations


# account name → new ida
NAME_TO_IDA = {
    'Cash': '1000-Cash',
    'Petty Cash': '1010-PettyCash',
    'Accounts Receivable': '1100-AR',
    'Other Receivables': '1110-OtherAR',
    'Inventory': '1200-Inventory',
    'Prepaid Expenses': '1300-Prepaid',
    'Equipment': '1500-Equipment',
    'Accumulated Depreciation': '1510-AccumDepr',
    'Accounts Payable': '2000-AP',
    'Sales Tax Payable': '2100-SalesTax',
    'Accrued Liabilities': '2200-Accrued',
    'Commissions Payable': '2210-CommPay',
    'Freight Payable': '2220-FreightPay',
    'Deferred Revenue': '2300-DeferredRev',
    'Notes Payable - Long Term': '2500-NotesPay',
    'Retained Earnings': '3000-Retained',
    'Paid-In Capital': '3100-PaidIn',
    'Net Profit / Loss': '3900-NetProfit',
    'Sales Revenue': '4000-Sales',
    'Freight Revenue': '4100-FreightRev',
    'Finance Charge Income': '4200-FinCharge',
    'Miscellaneous Income': '4900-MiscIncome',
    'Sales Returns & Allowances': '4910-Returns',
    'Sales Discounts Taken': '4920-Discounts',
    'Cost of Goods Sold': '5000-COGS',
    'Freight In / Landed Cost': '5100-FreightIn',
    'Inventory Clearing': '5200-InvClearing',
    'Wages & Salaries': '6000-Wages',
    'Payroll Tax Expense': '6010-PayrollTax',
    'Commission Expense': '6100-Commission',
    'Rent Expense': '6200-Rent',
    'Utilities Expense': '6300-Utilities',
    'Depreciation Expense': '6400-Depreciation',
    'Bad Debt Expense': '6500-BadDebt',
    'Marketing & Advertising': '6600-Marketing',
    'Travel & Entertainment': '6700-Travel',
    'Insurance Expense': '6800-Insurance',
    'Bank & Processing Fees': '6900-BankFees',
    'General & Administrative': '6950-GenAdmin',
}

# Old account_number values found in gl_journals.account → new ida
JOURNAL_ACCOUNT_MAP = {
    'ASSET-CASH-000': '1000-Cash',
    'ASSET-AR-000': '1100-AR',
    'ASSET-INVENTORY-000': '1200-Inventory',
    'REV-SALES-000': '4000-Sales',
    'COGS-PRODUCTS-000': '5000-COGS',
    'EXP-COMMISSIONS-000': '6100-Commission',
    'LIAB-COMMPAY-000': '2210-CommPay',
    'ZZZ-AP-000': 'zzz-2000-AP',
    'ZZZ-COGS-000': 'zzz-5000-COGS',
    'ZZZ-INVENTORY-000': 'zzz-1200-Inventory',
    'ZZZ-REV-000': 'zzz-4000-Sales',
    '4000': '4000-Sales',
}


def update_forward(apps, schema_editor):
    GlAccount = apps.get_model('accounts', 'GlAccount')
    GlJournal = apps.get_model('accounts', 'GlJournal')

    # Update GL account idas by name
    for acct in GlAccount.objects.all():
        new_ida = NAME_TO_IDA.get(acct.name)
        if new_ida:
            acct.ida = new_ida
            acct.save(update_fields=['ida'])

    # Update journal entries to use new ida values
    for old_val, new_ida in JOURNAL_ACCOUNT_MAP.items():
        GlJournal.objects.filter(account=old_val).update(account=new_ida)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_remove_gl_account_number'),
    ]

    operations = [
        migrations.RunPython(update_forward, migrations.RunPython.noop),
    ]
