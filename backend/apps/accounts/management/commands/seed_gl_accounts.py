"""
seed_gl_accounts — Seed the standard chart of accounts.

Usage:
    python manage.py seed_gl_accounts           # create missing accounts, fill blanks
    python manage.py seed_gl_accounts --force   # also overwrite name/type/category/used_for/summary

The GlAccount table is the chart of accounts — the authority for which accounts
exist (apps/accounts/services/chart.py). This command only seeds it.

Numbering: 1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx revenue (49xx contra
revenue), 5xxx cost of sales, 6xxx operating expense, 7xxx other income & expense.
Types carry the normal balance, categories the statement section (services/chart.py).
ida format: {number}-{lowercase_words}, e.g. 1100-accounts_receivable.
Each account's summary is written to comments.process (key=account_use).
"""
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.chart import ACCOUNT_CODE_PATTERN

A, CA = 'asset', 'contra_asset'
L = 'liability'
E, CE = 'equity', 'contra_equity'
R, CR = 'revenue', 'contra_revenue'
COS, X = 'cost_of_sales', 'expense'
OI, OX = 'other_income', 'other_expense'

# (ida, name, type, category, used_for, summary)
# The summary teaches: what belongs here, what moves it, and where it goes next. The
# type gives the normal balance (chart.NORMAL_BALANCE); the category gives the statement
# section (chart.SECTIONS).
ACCOUNTS = [
    # ── Assets (1xxx) — what the business owns ──
    ('1000-cash', 'Cash', A, 'cash', 'cash',
     'Money in the bank. Increases (debit) when a customer pays; decreases (credit) when we pay a vendor or an expense. Reconcile to the bank statement every month. Role: undeposited_funds.'),
    ('1010-petty_cash', 'Petty Cash', A, 'cash', 'cash',
     'Cash kept on hand for small purchases. Refill it from 1000-cash; each refill debits the expenses the receipts show.'),
    ('1100-accounts_receivable', 'Accounts Receivable', A, 'receivables', 'receivables',
     'What customers owe us. An invoice debits it for its full total (goods + tax + shipping + other); a customer payment, a credit memo, or a small-balance write-off credits it. Role: accounts_receivable.'),
    ('1110-other_receivables', 'Other Receivables', A, 'receivables', 'receivables',
     'Money owed to us that is not a customer invoice: manufacturer rebates, employee advances, vendor refunds, insurance claims. Kept out of the customer aging. Role: other_receivables.'),
    ('1200-inventory', 'Inventory', A, 'inventory', 'inventory',
     'Goods on hand, at cost. Receiving a purchase debits it; shipping on an invoice credits it (the cost moves to 5000-cost_of_goods_sold), as do scrap and builds that use components. Role: inventory.'),
    ('1210-work_in_process', 'Work in Process', A, 'inventory', 'inventory',
     'Parts and labor released to a workorder and not yet built. Release debits it (parts from 1200-inventory, labor estimate from 2160-labor_applied); completion credits it into 1200-inventory. Role: work_in_process.'),
    ('1300-prepaid_expenses', 'Prepaid Expenses', A, 'other_current_assets', 'posting',
     'Expenses paid before the months they cover: insurance, rent, annual subscriptions. Each month, credit it and debit the expense for the part used.'),
    ('1500-equipment', 'Equipment', A, 'fixed_assets', 'posting',
     'Equipment, vehicles and furniture that last more than a year, at what they cost. A capital purchase posts here instead of to an expense.'),
    ('1510-accumulated_depreciation', 'Accumulated Depreciation', CA, 'fixed_assets', 'posting',
     'Wear on equipment, taken a little each period. Reduces 1500-equipment on the balance sheet (a contra asset: credit balance). Credited with each debit to 6400-depreciation.'),

    # ── Liabilities (2xxx) — what the business owes ──
    ('2000-accounts_payable', 'Accounts Payable', L, 'current_liabilities', 'payables',
     'What we owe vendors. A vendor bill credits it; paying the vendor debits it. Role: accounts_payable.'),
    ('2050-received_not_billed', 'Received Not Billed', L, 'current_liabilities', 'posting',
     'Goods received before the vendor has billed us. Credited at receipt (with the debit to 1200-inventory); debited when the bill arrives and moves the amount to 2000-accounts_payable. A balance left over is a receipt and a bill that do not match — investigate it.'),
    ('2100-sales_tax_payable', 'Sales Tax Payable', L, 'current_liabilities', 'tax',
     'Sales tax collected from customers — it belongs to the taxing authority, not to us. Each invoice credits it; paying the tax debits it. Report by jurisdiction. Role: sales_tax_payable.'),
    ('2150-payroll_liabilities', 'Payroll Liabilities', L, 'current_liabilities', 'posting',
     'Taxes and deductions withheld from paychecks and the employer taxes owed, until they are paid over. Payroll credits it; each payment to the tax agency or benefit provider debits it.'),
    ('2160-labor_applied', 'Labor Applied', L, 'current_liabilities', 'posting',
     'Clearing account for labor estimated into builds. A BOM labor line (hours × factor × rate) credits it at release. Accounting debits actual payroll against it and moves what is left to 5320-labor_variance. Role: labor_applied.'),
    ('2200-accrued_liabilities', 'Accrued Liabilities', L, 'current_liabilities', 'posting',
     'Costs already incurred but not yet billed: wages earned since the last payday, utilities used. Credited at period end; cleared when the bill is paid.'),
    ('2210-commissions_payable', 'Commissions Payable', L, 'current_liabilities', 'payables',
     'Commissions reps have earned and we have not yet paid. Credited when an invoice posts its commission (with 6100-commission_expense); debited when the rep is paid. Role: commission_payable.'),
    ('2220-freight_payable', 'Freight Payable', L, 'current_liabilities', 'payables',
     'What we owe carriers for shipments already made. A carrier bill credits it; paying the carrier debits it.'),
    ('2300-deferred_revenue', 'Deferred Revenue', L, 'current_liabilities', 'posting',
     'Money received for goods or services not yet delivered: deposits and prepayments. It is owed to the customer until earned, then moves to revenue.'),
    ('2500-notes_payable', 'Notes Payable', L, 'long_term_liabilities', 'posting',
     'Loans due after more than a year. Borrowing credits it; the principal part of each loan payment debits it (the interest part goes to 7200-interest_expense).'),

    # ── Equity (3xxx) — what the owners have in the business ──
    ('3000-retained_earnings', 'Retained Earnings', E, 'equity', 'posting',
     'Profits kept in the business over the years. At year end the year\'s net income closes into it. Role: retained_earnings.'),
    ('3100-owner_investment', 'Owner Investment', E, 'equity', 'posting',
     'Money the owners put into the business. Credited when an owner invests.'),
    ('3200-owner_draws', 'Owner Draws', CE, 'equity', 'posting',
     'Money the owners take out of the business for themselves — not a business expense. Debited on each draw (a contra equity account: debit balance); closed into 3000-retained_earnings at year end.'),
    ('3900-current_year_earnings', 'Current Year Earnings', E, 'equity', 'reporting',
     'This year\'s net income so far — revenue minus every cost and expense — shown on the balance sheet. Computed, never posted; closed into 3000-retained_earnings at year end.'),

    # ── Revenue (4xxx) — what the business earns ──
    ('4000-sales_revenue', 'Sales', R, 'revenue', 'sales',
     'Revenue from goods sold. Each invoice line credits it for its amount after line discounts. An item or customer can name a more specific revenue account. Role: sales_revenue.'),
    ('4010-service_revenue', 'Service Revenue', R, 'revenue', 'sales',
     'Revenue from services and labor billed: consulting, trades, installation, travel, call-outs. Service items name it as their revenue account.'),
    ('4100-shipping_revenue', 'Shipping & Handling Income', R, 'revenue', 'sales',
     'Shipping and handling charged to customers. An invoice\'s shipping total credits it. What carriers charge us is 5100-freight_in. Role: shipping_revenue.'),
    ('4200-finance_charge_income', 'Finance Charge Income', R, 'revenue', 'sales',
     'Finance charges on past-due customer balances, credited when the monthly assessment posts. Role: finance_charge_income.'),
    ('4900-miscellaneous_income', 'Miscellaneous Income', R, 'revenue', 'sales',
     'Income from operations that is not a sale: manufacturer rebates, card surcharges under dual pricing, an invoice\'s other charges. Role: other_income.'),
    ('4910-sales_returns', 'Sales Returns & Allowances', CR, 'revenue', 'posting',
     'Goods customers return and price allowances we give. Credit memos debit it, so 4000-sales_revenue keeps the gross figure (a contra revenue account: debit balance).'),
    ('4920-sales_discounts', 'Sales Discounts', CR, 'revenue', 'discounts',
     'Early-payment discounts customers take. Debited when a payment is applied with a discount so the invoice closes. Line discounts are not here; lines post net. Role: discount_given.'),
    ('4930-small_balance_writeoff', 'Small Balance Write-Off', CR, 'revenue', 'posting',
     'Leftover balances too small to chase, dismissed when a payment is applied. Debited here, credited to 1100-accounts_receivable. A rounding decision, not a credit loss (that is 6500-bad_debt). Role: small_balance_writeoff.'),

    # ── Cost of sales (5xxx) — what the goods we sold cost us ──
    ('5000-cost_of_goods_sold', 'Cost of Goods Sold', COS, 'cost_of_sales', 'cogs',
     'What the goods on an invoice cost us, at the company costing method. Debited when the invoice posts, with a credit to 1200-inventory. Sales minus this is gross profit. Role: cost_of_goods_sold.'),
    ('5100-freight_in', 'Freight In', COS, 'cost_of_sales', 'cogs',
     'Freight and landed costs to bring goods in. Carrier bills on purchases debit it, unless landed costing adds them to inventory cost.'),
    ('5300-scrap_shrinkage', 'Scrap & Shrinkage', COS, 'cost_of_sales', 'posting',
     'Inventory lost to damage, theft or count differences. Debited by scrap and negative adjustments, credited to 1200-inventory — its own account so loss is visible, not buried in cost of goods. Role: scrap.'),
    ('5310-inventory_cost_variance', 'Inventory Cost Variance', COS, 'cost_of_sales', 'posting',
     'The difference between the provisional cost used when stock ran short and the actual cost of the stock that filled the shortage. Role: inventory_cost_variance.'),
    ('5320-labor_variance', 'Labor Variance', COS, 'cost_of_sales', 'posting',
     'Actual payroll minus the labor estimated into builds, posted when 2160-labor_applied is reconciled. Role: labor_variance.'),

    # ── Operating expenses (6xxx) — the cost of running the business ──
    ('6000-wages', 'Wages & Salaries', X, 'operating_expenses', 'expense',
     'Gross pay before withholding. Payroll debits it; the net pay credits 1000-cash and the withholding credits 2150-payroll_liabilities.'),
    ('6010-payroll_tax', 'Payroll Taxes', X, 'operating_expenses', 'expense',
     'The employer\'s share of payroll taxes: Social Security and Medicare match, unemployment. Debited by payroll, credited to 2150-payroll_liabilities.'),
    ('6100-commission_expense', 'Commissions', X, 'operating_expenses', 'expense',
     'Commissions reps earn on invoiced sales, debited when an invoice posts its commission, with 2210-commissions_payable. Role: commission_expense.'),
    ('6150-professional_fees', 'Professional Fees', X, 'operating_expenses', 'expense',
     'Accountants, lawyers, consultants and other outside professionals.'),
    ('6200-rent', 'Rent', X, 'operating_expenses', 'expense',
     'Rent for offices, warehouses and stations.'),
    ('6250-repairs_maintenance', 'Repairs & Maintenance', X, 'operating_expenses', 'expense',
     'Repairs and upkeep of equipment, vehicles and premises that keep them working. An improvement that adds years of life is equipment (1500), not a repair.'),
    ('6300-utilities', 'Utilities', X, 'operating_expenses', 'expense',
     'Electricity, gas, water, internet and phones for the business premises.'),
    ('6350-office_software', 'Office Supplies & Software', X, 'operating_expenses', 'expense',
     'Office supplies, postage, and software subscriptions.'),
    ('6400-depreciation', 'Depreciation', X, 'operating_expenses', 'expense',
     'This period\'s share of the cost of equipment. Debited here, credited to 1510-accumulated_depreciation.'),
    ('6450-taxes_licenses', 'Taxes & Licenses', X, 'operating_expenses', 'expense',
     'Business licenses, permits, and property and franchise taxes. Not sales tax (that is owed to the state, 2100) and not payroll taxes (6010) or income tax.'),
    ('6500-bad_debt', 'Bad Debt', X, 'operating_expenses', 'expense',
     'Customer balances we will not collect. Writing one off debits it and credits 1100-accounts_receivable (the direct write-off method small businesses use). Role: bad_debt_writeoff.'),
    ('6600-marketing', 'Marketing & Advertising', X, 'operating_expenses', 'expense',
     'Advertising, promotion, trade shows and marketing services.'),
    ('6700-travel_meals', 'Travel & Meals', X, 'operating_expenses', 'expense',
     'Business travel, lodging and meals. Entertainment is kept apart from meals because the tax rules treat them differently.'),
    ('6800-insurance', 'Insurance', X, 'operating_expenses', 'expense',
     'Insurance for the current period. Premiums paid ahead sit in 1300-prepaid_expenses until used.'),
    ('6900-bank_fees', 'Bank & Card Fees', X, 'operating_expenses', 'expense',
     'Bank charges and card processing fees, debited when a payment settles net of fees.'),
    ('6950-general_admin', 'General & Administrative', X, 'operating_expenses', 'expense',
     'Running costs with no more specific account. Role: default_expense. If it grows, open a specific account for what is in it.'),

    # ── Other income & expense (7xxx) — outside day-to-day operations ──
    ('7000-interest_income', 'Interest Income', OI, 'other', 'posting',
     'Interest earned on bank balances and loans we have made.'),
    ('7100-fx_gain_loss', 'Foreign Exchange Gain/Loss', OX, 'other', 'posting',
     'Gains and losses when a foreign-currency invoice is paid at a different exchange rate. A debit is a loss, a credit is a gain; a credit balance is a net gain. Role: fx_gain_loss.'),
    ('7200-interest_expense', 'Interest Expense', OX, 'other', 'posting',
     'Interest paid on loans and credit lines — the interest part of each loan payment on 2500-notes_payable.'),
]

# Company profile config.gl_defaults — which account each posting role uses.
GL_DEFAULTS = {
    'accounts_receivable': '1100-accounts_receivable',
    'other_receivables': '1110-other_receivables',
    'undeposited_funds': '1000-cash',
    'inventory': '1200-inventory',
    'work_in_process': '1210-work_in_process',
    'accounts_payable': '2000-accounts_payable',
    'labor_applied': '2160-labor_applied',
    'sales_tax_payable': '2100-sales_tax_payable',
    'commission_payable': '2210-commissions_payable',
    'retained_earnings': '3000-retained_earnings',
    'sales_revenue': '4000-sales_revenue',
    'shipping_revenue': '4100-shipping_revenue',
    'other_income': '4900-miscellaneous_income',
    'finance_charge_income': '4200-finance_charge_income',
    'discount_given': '4920-sales_discounts',
    'small_balance_writeoff': '4930-small_balance_writeoff',
    'bad_debt_writeoff': '6500-bad_debt',
    'cost_of_goods_sold': '5000-cost_of_goods_sold',
    'inventory_cost_variance': '5310-inventory_cost_variance',
    'labor_variance': '5320-labor_variance',
    'scrap': '5300-scrap_shrinkage',
    'commission_expense': '6100-commission_expense',
    'default_expense': '6950-general_admin',
    'fx_gain_loss': '7100-fx_gain_loss',
}

# Accounts this chart replaced (old code → new code, or None where the account is gone).
# Every reference moves with them; see apps/accounts/management/commands/retire_gl_accounts.py.
REPLACED = {
    '3900-net_profit': '3900-current_year_earnings',
    '4100-freight_revenue': '4100-shipping_revenue',
    '5200-inventory_clearing': '2050-received_not_billed',
    '6960-writeoff': '6500-bad_debt',
    '6700-travel': '6700-travel_meals',
    '3100-paid_in_capital': '3100-owner_investment',
}




from apps.core.services.comment_stamp import append_comment

class Command(BaseCommand):
    help = f'Seed the standard chart of accounts ({len(ACCOUNTS)} accounts)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite name/type/category/used_for/summary on existing accounts')

    def handle(self, *args, **options):
        force = options.get('force')
        bad = [a[0] for a in ACCOUNTS if not ACCOUNT_CODE_PATTERN.match(a[0])]
        if bad:
            raise ValueError(f'Account codes not in {{number}}-{{lowercase_words}} style: {bad}')

        created = updated = 0
        with transaction.atomic():
            for ida, name, acct_type, category, used_for, summary in ACCOUNTS:
                account = GlAccount.objects.filter(ida=ida).first()
                is_new = account is None
                if is_new:
                    account = GlAccount(ida=ida, is_active=True)
                fields = {'name': name, 'type': acct_type, 'category': category, 'used_for': used_for}
                for field, value in fields.items():
                    if is_new or force or not getattr(account, field):
                        setattr(account, field, value)
                comments = account.comments if isinstance(account.comments, dict) else {}
                process = comments.get('process') or []
                has_use = any(isinstance(c, dict) and c.get('key') == 'account_use' for c in process)
                if is_new or force or not has_use:
                    comments['process'] = [c for c in process
                                           if not (isinstance(c, dict) and c.get('key') == 'account_use')]
                    account.comments = comments
                    append_comment(account, 'process', summary, source='seed_gl_accounts',
                                   key='account_use')
                account.save()
                created += is_new
                updated += not is_new

        self.stdout.write(self.style.SUCCESS(f'GL accounts: {created} created, {updated} checked/updated'))
