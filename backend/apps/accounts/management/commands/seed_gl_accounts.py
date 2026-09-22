"""
seed_gl_accounts — Seed the standard chart of accounts.

Usage:
    python manage.py seed_gl_accounts           # create missing accounts, fill blanks
    python manage.py seed_gl_accounts --force   # also overwrite name/type/category/used_for/summary

The GlAccount table is the chart of accounts — the authority for which accounts
exist (apps/accounts/services/chart.py). This command only seeds it.

Numbering: 1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx revenue (49xx contra
revenue), 5xxx cost of sales, 6xxx operating expense, 7xxx other.
ida format: {number}-{lowercase_words}, e.g. 1100-accounts_receivable.
Each account's summary is written to comments.process (kind=account_use).
"""
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.chart import ACCOUNT_CODE_PATTERN

A, L, E, R, C, X = 'asset', 'liability', 'equity', 'revenue', 'contra', 'expense'

# (ida, name, type, category, used_for, summary)
ACCOUNTS = [
    # ── Assets (1xxx) ──
    ('1000-cash', 'Cash', A, 'cash', 'cash',
     'Money in bank and deposit accounts. Debited when a customer cash is received, credited when a vendor bill or expense is paid. Reconcile to the bank statement monthly. Role: undeposited_funds.'),
    ('1010-petty_cash', 'Petty Cash', A, 'cash', 'cash',
     'Cash kept on hand for small purchases. Replenish from 1000-cash; each replenishment debits the expenses the receipts show.'),
    ('1100-accounts_receivable', 'Accounts Receivable', A, 'receivables', 'receivables',
     'What customers owe us. Debited by an invoice for its full total (goods + tax + shipping + other); credited when a cash entry is applied, a credit memo issues, or a small balance is written off. Role: accounts_receivable.'),
    ('1110-other_receivables', 'Other Receivables', A, 'receivables', 'receivables',
     'Amounts owed to us that are not customer invoices: manufacturer rebates earned, employee advances, vendor refunds due, insurance claims. Kept out of the customer aging. Role: other_receivables.'),
    ('1200-inventory', 'Inventory', A, 'inventory', 'inventory',
     'Goods on hand at cost. Debited when a purchase is received; credited by the cost of goods an invoice ships (with 5000-cost_of_goods_sold), by scrap (5300-scrap_shrinkage), and by builds that consume components. Role: inventory.'),
    ('1210-work_in_process', 'Work in Process', A, 'inventory', 'inventory',
     'Parts and labor released to a workorder and not yet built. Debited at release by the issued cost of parts (credit 1200-inventory) and the estimated labor (credit 2160-labor_applied); credited at completion into 1200-inventory for the built item. Balance = Σ open in_process value. Role: work_in_process.'),
    ('1300-prepaid_expenses', 'Prepaid Expenses', A, 'prepaid', 'posting',
     'Expenses paid before the period they cover: insurance, rent, annual subscriptions. Credit it and debit the expense as each period is used.'),
    ('1500-equipment', 'Equipment', A, 'fixed_assets', 'posting',
     'Long-lived equipment and vehicles at purchase cost. Capital purchases (is_capital) post here instead of to an expense account.'),
    ('1510-accumulated_depreciation', 'Accumulated Depreciation', A, 'depreciation', 'posting',
     'Depreciation taken against 1500-equipment (contra asset, credit balance). Credited each period by the entry that debits 6400-depreciation.'),

    # ── Liabilities (2xxx) ──
    ('2000-accounts_payable', 'Accounts Payable', L, 'payables', 'payables',
     'What we owe vendors. Credited when a purchase is received or a vendor bill is entered; debited when the vendor is paid. Role: accounts_payable.'),
    ('2100-sales_tax_payable', 'Sales Tax Payable', L, 'tax', 'tax',
     'Sales tax collected from customers and owed to the taxing jurisdiction. Credited by the tax on each invoice; debited when the tax is remitted. Report by jurisdiction (tax_summary_by_period). Role: sales_tax_payable.'),
    ('2160-labor_applied', 'Labor Applied', L, 'payables', 'posting',
     'Clearing account for labor estimated into builds. WebClerk does not do labor: a BOM labor line is an estimate (hours x factor x rate) credited here at release. Accounting debits actual payroll against it and moves what is left to 5320-labor_variance. Role: labor_applied.'),
    ('2200-accrued_liabilities', 'Accrued Liabilities', L, 'payables', 'posting',
     'Expenses incurred but not yet billed or paid: wages earned, utilities used. Credited by the accrual at period end; cleared when the bill is paid.'),
    ('2210-commissions_payable', 'Commissions Payable', L, 'payables', 'payables',
     'Commissions earned by reps and not yet paid. Credited when an invoice journalizes and its commission accrues (with 6100-commission_expense); debited when the rep is paid. Role: commission_payable.'),
    ('2220-freight_payable', 'Freight Payable', L, 'payables', 'payables',
     'Freight owed to carriers for shipments already made. Credited when a carrier bill is recorded; debited when the carrier is paid.'),
    ('2300-deferred_revenue', 'Deferred Revenue', L, 'payables', 'posting',
     'Money received for goods or services not yet delivered: deposits, prepayments, deferred invoices. Moves to revenue when earned.'),
    ('2500-notes_payable', 'Notes Payable - Long Term', L, 'payables', 'posting',
     'Long-term loans and notes. Credited when funds are borrowed; debited by the principal portion of each cash entry (interest goes to expense).'),

    # ── Equity (3xxx) ──
    ('3000-retained_earnings', 'Retained Earnings', E, 'equity', 'posting',
     'Accumulated profits kept in the business. Closed into once a year from 3900-net_profit; debited by owner distributions. Role: retained_earnings.'),
    ('3100-paid_in_capital', 'Paid-In Capital', E, 'equity', 'posting',
     'Capital the owners put into the business. Credited when owners contribute funds.'),
    ('3900-net_profit', 'Net Profit / Loss', E, 'equity', 'reporting',
     'Current-year profit or loss (revenue minus expenses), computed for the balance sheet. Never posted directly; closed into 3000-retained_earnings at year end.'),

    # ── Revenue (4xxx) ──
    ('4000-sales_revenue', 'Sales Revenue', R, 'sales', 'sales',
     "Revenue from goods sold. Credited by each invoice line's extended amount (net of line discounts). An item or customer can name a more specific revenue account. Role: sales_revenue."),
    ('4010-service_revenue', 'Service Revenue', R, 'sales', 'sales',
     'Revenue from services and labor billed: consulting, trades, labor, travel, call-outs. Service items name it in gls.revenue; credited by their invoice lines.'),
    ('4100-freight_revenue', 'Freight Revenue', R, 'sales', 'sales',
     "Shipping and handling charged to customers. Credited by an invoice's shipping total. What carriers charge us is 5100-freight_in or 2220-freight_payable. Role: shipping_revenue."),
    ('4200-finance_charge_income', 'Finance Charge Income', R, 'sales', 'sales',
     'Finance charges on past-due customer balances (company config.receivables). Credited by finance_charge invoice lines when the monthly assessment journalizes. Role: finance_charge_income.'),
    ('4900-miscellaneous_income', 'Miscellaneous Income', R, 'sales', 'sales',
     "Income that is not a sale: interest earned, manufacturer rebates, card surcharges under dual pricing, an invoice's other charges. Role: other_income."),
    ('4910-sales_returns', 'Sales Returns & Allowances', C, 'contra', 'posting',
     'Returned goods and allowances (contra revenue, debit balance). Debited by credit memos so 4000-sales_revenue keeps the gross figure.'),
    ('4920-sales_discounts', 'Sales Discounts Taken', C, 'contra', 'discounts',
     'Early-payment discounts customers take (contra revenue). Debited when a cash entry is applied with a discount so the invoice closes. Line discounts are not posted here; lines post net. Role: discount_given.'),
    ('4930-small_balance_writeoff', 'Small Balance Write-Off', C, 'contra', 'posting',
     'Leftover balances not worth collecting, written off when a cash entry is applied with dismiss_balance. Debited here, credited to 1100-accounts_receivable. Role: small_balance_writeoff.'),

    # ── Cost of sales (5xxx) ──
    ('5000-cost_of_goods_sold', 'Cost of Goods Sold', X, 'cogs', 'cogs',
     'Cost of the goods an invoice ships, at the company costing_method. Debited when the invoice journalizes, with a credit to 1200-inventory. Role: cost_of_goods_sold.'),
    ('5100-freight_in', 'Freight In / Landed Cost', X, 'cogs', 'cogs',
     'Freight and landed costs to bring goods in. Debited by carrier bills on purchases, or capitalized into inventory cost when landed costing is on.'),
    ('5200-inventory_clearing', 'Inventory Clearing', X, 'cogs', 'cogs',
     'Holding account between a purchase receipt and the vendor bill. Debited at receipt, credited when the bill arrives; a balance left over is a receipt/bill mismatch to investigate.'),
    ('5300-scrap_shrinkage', 'Scrap & Shrinkage', X, 'cogs', 'posting',
     'Inventory lost to damage, shrinkage, or count adjustments. Debited by scrap and negative adjustments, credited to 1200-inventory. Role: scrap.'),
    ('5310-inventory_cost_variance', 'Inventory Cost Variance', X, 'cogs', 'posting',
     'Difference between the provisional cost an issue was valued at when stock was short and the actual cost of the stock that later filled it. Posted by the deficit true-up. An item may name its own account in gls.variance. Role: inventory_cost_variance.'),
    ('5320-labor_variance', 'Labor Variance', X, 'cogs', 'posting',
     'Actual payroll minus the labor estimated into builds. Accounting posts it when reconciling 2160-labor_applied; name the labor item so its learned factor can be computed. Role: labor_variance.'),

    # ── Operating expenses (6xxx) ──
    ('6000-wages', 'Wages & Salaries', X, 'payroll', 'expense',
     'Gross wages and salaries. Debited by payroll; credits go to cash and the payroll liabilities.'),
    ('6010-payroll_tax', 'Payroll Tax Expense', X, 'payroll', 'expense',
     'Employer payroll taxes: FICA match, unemployment. Debited by payroll.'),
    ('6100-commission_expense', 'Commission Expense', X, 'expense', 'expense',
     'Commissions earned by reps on invoiced sales. Debited when an invoice journalizes and its commission accrues, with 2210-commissions_payable. Role: commission_expense.'),
    ('6200-rent', 'Rent Expense', X, 'expense', 'expense',
     'Rent for offices, warehouses, and stations.'),
    ('6300-utilities', 'Utilities Expense', X, 'expense', 'expense',
     'Electricity, water, internet, phone.'),
    ('6400-depreciation', 'Depreciation Expense', X, 'expense', 'expense',
     'Periodic depreciation of equipment. Debited here, credited to 1510-accumulated_depreciation.'),
    ('6500-bad_debt', 'Bad Debt Expense', X, 'expense', 'expense',
     'Customer balances judged uncollectible under the allowance method. Direct write-offs use 6960-writeoff.'),
    ('6600-marketing', 'Marketing & Advertising', X, 'expense', 'expense',
     'Advertising, promotion, trade shows, marketing services.'),
    ('6700-travel', 'Travel & Entertainment', X, 'expense', 'expense',
     'Business travel, lodging, meals, entertainment.'),
    ('6800-insurance', 'Insurance Expense', X, 'expense', 'expense',
     'Insurance for the current period. Prepaid premiums sit in 1300-prepaid_expenses until used.'),
    ('6900-bank_fees', 'Bank & Processing Fees', X, 'expense', 'expense',
     'Bank charges and card processing fees. Debited when a cash entry settles net of fees.'),
    ('6950-general_admin', 'General & Administrative', X, 'expense', 'expense',
     'General and administrative costs with no more specific account. Role: default_expense. If it grows, open a specific account.'),
    ('6960-writeoff', 'Bad Debt / Write-Off Expense', X, 'expense', 'expense',
     'Customer balances written off directly as uncollectible. Debited here, credited to 1100-accounts_receivable. Role: bad_debt_writeoff.'),

    # ── Other (7xxx) ──
    ('7100-fx_gain_loss', 'Foreign Exchange Gain/Loss', X, 'other', 'posting',
     'Gains and losses when a foreign-currency invoice is paid at a different exchange rate. Debit is a loss, credit is a gain. Role: fx_gain_loss.'),
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
    'shipping_revenue': '4100-freight_revenue',
    'other_income': '4900-miscellaneous_income',
    'finance_charge_income': '4200-finance_charge_income',
    'discount_given': '4920-sales_discounts',
    'small_balance_writeoff': '4930-small_balance_writeoff',
    'bad_debt_writeoff': '6960-writeoff',
    'cost_of_goods_sold': '5000-cost_of_goods_sold',
    'inventory_cost_variance': '5310-inventory_cost_variance',
    'labor_variance': '5320-labor_variance',
    'scrap': '5300-scrap_shrinkage',
    'commission_expense': '6100-commission_expense',
    'default_expense': '6950-general_admin',
    'fx_gain_loss': '7100-fx_gain_loss',
}


def account_use_comment(summary: str) -> dict:
    return {
        'by': 'seed_gl_accounts',
        'dt': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'text': summary,
        'kind': 'account_use',
        'capacity': 'ops',
        'replaces': None,
    }


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
                has_use = any(isinstance(c, dict) and c.get('kind') == 'account_use' for c in process)
                if is_new or force or not has_use:
                    process = [c for c in process if not (isinstance(c, dict) and c.get('kind') == 'account_use')]
                    process.append(account_use_comment(summary))
                    comments['process'] = process
                    account.comments = comments
                account.save()
                created += is_new
                updated += not is_new

        self.stdout.write(self.style.SUCCESS(f'GL accounts: {created} created, {updated} checked/updated'))
