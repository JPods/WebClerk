"""
seed_gl_accounts — Seed the standard chart of accounts.

Usage:
    python manage.py seed_gl_accounts
    python manage.py seed_gl_accounts --force   # delete and re-seed

39 universal accounts using the 4-digit numbering convention:
  1xxx = Assets, 2xxx = Liabilities, 3xxx = Equity,
  4xxx = Revenue, 5xxx = COGS, 6xxx = Expenses.

ida format: {number}-{CamelCaseName} (e.g., 1000-Cash)
"""
from django.core.management.base import BaseCommand
from apps.accounts.models.gl_account import GlAccount


ACCOUNTS = [
    # ── Assets (1xxx) ──
    {'ida': '1000-Cash',       'name': 'Cash',                     'type': 'asset',     'category': 'cash',        'used_for': 'cash'},
    {'ida': '1010-PettyCash',  'name': 'Petty Cash',               'type': 'asset',     'category': 'cash'},
    {'ida': '1100-AR',         'name': 'Accounts Receivable',      'type': 'asset',     'category': 'receivables', 'used_for': 'receivables'},
    {'ida': '1110-OtherAR',    'name': 'Other Receivables',        'type': 'asset',     'category': 'receivables'},
    {'ida': '1200-Inventory',  'name': 'Inventory',                'type': 'asset',     'category': 'inventory',   'used_for': 'inventory'},
    {'ida': '1300-Prepaid',    'name': 'Prepaid Expenses',         'type': 'asset',     'category': 'receivables'},
    {'ida': '1500-Equipment',  'name': 'Equipment',                'type': 'asset',     'category': ''},
    {'ida': '1510-AccumDepr',  'name': 'Accumulated Depreciation', 'type': 'asset',     'category': ''},

    # ── Liabilities (2xxx) ──
    {'ida': '2000-AP',         'name': 'Accounts Payable',         'type': 'liability', 'category': 'payables',    'used_for': 'payables'},
    {'ida': '2100-SalesTax',   'name': 'Sales Tax Payable',        'type': 'liability', 'category': 'payables',    'used_for': 'tax_payable'},
    {'ida': '2200-Accrued',    'name': 'Accrued Liabilities',      'type': 'liability', 'category': 'payables'},
    {'ida': '2210-CommPay',    'name': 'Commissions Payable',      'type': 'liability', 'category': 'payables'},
    {'ida': '2220-FreightPay', 'name': 'Freight Payable',          'type': 'liability', 'category': 'payables'},
    {'ida': '2300-DeferredRev','name': 'Deferred Revenue',         'type': 'liability', 'category': 'payables'},
    {'ida': '2500-NotesPay',   'name': 'Notes Payable - Long Term','type': 'liability', 'category': 'payables'},

    # ── Equity (3xxx) ──
    {'ida': '3000-Retained',   'name': 'Retained Earnings',        'type': 'equity',    'category': ''},
    {'ida': '3100-PaidIn',     'name': 'Paid-In Capital',          'type': 'equity',    'category': ''},
    {'ida': '3900-NetProfit',  'name': 'Net Profit / Loss',        'type': 'equity',    'category': ''},

    # ── Revenue (4xxx) ──
    {'ida': '4000-Sales',      'name': 'Sales Revenue',            'type': 'revenue',   'category': 'sales',       'used_for': 'sales'},
    {'ida': '4100-FreightRev', 'name': 'Freight Revenue',          'type': 'revenue',   'category': 'sales'},
    {'ida': '4200-FinCharge',  'name': 'Finance Charge Income',    'type': 'revenue',   'category': 'sales'},
    {'ida': '4900-MiscIncome', 'name': 'Miscellaneous Income',     'type': 'revenue',   'category': 'sales'},
    {'ida': '4910-Returns',    'name': 'Sales Returns & Allowances','type': 'contra',   'category': ''},
    {'ida': '4920-Discounts',  'name': 'Sales Discounts Taken',    'type': 'contra',    'category': ''},

    # ── COGS (5xxx) ──
    {'ida': '5000-COGS',       'name': 'Cost of Goods Sold',       'type': 'expense',   'category': 'cogs',        'used_for': 'cogs'},
    {'ida': '5100-FreightIn',  'name': 'Freight In / Landed Cost', 'type': 'expense',   'category': 'cogs'},
    {'ida': '5200-InvClearing','name': 'Inventory Clearing',       'type': 'expense',   'category': 'cogs'},

    # ── Expenses (6xxx) ──
    {'ida': '6000-Wages',      'name': 'Wages & Salaries',         'type': 'expense',   'category': 'expense'},
    {'ida': '6010-PayrollTax', 'name': 'Payroll Tax Expense',      'type': 'expense',   'category': 'expense'},
    {'ida': '6100-Commission', 'name': 'Commission Expense',       'type': 'expense',   'category': 'expense',     'used_for': 'commission'},
    {'ida': '6200-Rent',       'name': 'Rent Expense',             'type': 'expense',   'category': 'expense'},
    {'ida': '6300-Utilities',  'name': 'Utilities Expense',        'type': 'expense',   'category': 'expense'},
    {'ida': '6400-Depreciation','name': 'Depreciation Expense',    'type': 'expense',   'category': 'expense'},
    {'ida': '6500-BadDebt',    'name': 'Bad Debt Expense',         'type': 'expense',   'category': 'expense'},
    {'ida': '6600-Marketing',  'name': 'Marketing & Advertising',  'type': 'expense',   'category': 'expense'},
    {'ida': '6700-Travel',     'name': 'Travel & Entertainment',   'type': 'expense',   'category': 'expense'},
    {'ida': '6800-Insurance',  'name': 'Insurance Expense',        'type': 'expense',   'category': 'expense'},
    {'ida': '6900-BankFees',   'name': 'Bank & Processing Fees',   'type': 'expense',   'category': 'expense'},
    {'ida': '6950-GenAdmin',   'name': 'General & Administrative', 'type': 'expense',   'category': 'expense',     'used_for': 'expense'},
]


class Command(BaseCommand):
    help = 'Seed the standard chart of accounts (39 accounts)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing and re-seed')

    def handle(self, *args, **options):
        if options.get('force'):
            deleted, _ = GlAccount.objects.exclude(ida__startswith='zzz').delete()
            self.stdout.write(f'Deleted {deleted} existing GL accounts')

        created = skipped = 0
        for acct in ACCOUNTS:
            if GlAccount.objects.filter(ida=acct['ida']).exists():
                skipped += 1
                continue

            GlAccount.objects.create(
                ida=acct['ida'],
                name=acct['name'],
                type=acct.get('type', ''),
                category=acct.get('category', ''),
                used_for=acct.get('used_for', ''),
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'GL accounts: {created} created, {skipped} already exist'))
