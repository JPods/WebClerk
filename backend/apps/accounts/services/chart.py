"""Chart of accounts — the one authority for which GL accounts exist.

The GlAccount table is the chart. Every account code used anywhere — a journal
posting, an item's gls, an org's gl_accounts, a tax jurisdiction, the company
role defaults — must be an active GlAccount. Using any other code raises
UndefinedAccountError; nothing falls back to a guessed account.

Role defaults (which account an invoice's tax, freight, AR... post to) live in
the company profile Setting: config.gl_defaults.{role} = account code.

Code style: {4-digit number}-{lowercase_words}, e.g. 1100-accounts_receivable — the
number for the accountant, the words for everyone learning.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from django.apps import apps as dj_apps
from django.core.exceptions import ValidationError

ACCOUNT_CODE_PATTERN = re.compile(r'^\d{4}-[a-z0-9]+(?:_[a-z0-9]+)*$')

# ── How the chart reads ───────────────────────────────────────────────
# Numbers: 1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx revenue (49xx its contra
# accounts), 5xxx cost of sales, 6xxx operating expenses, 7xxx other income & expense.
#
# Every account type has a normal balance — the side that increases it. Assets and
# expenses grow with debits; liabilities, equity and revenue grow with credits. A contra
# account reduces the accounts it sits with, so it carries the opposite balance.
NORMAL_BALANCE = {
    'asset': 'debit', 'contra_asset': 'credit',
    'liability': 'credit',
    'equity': 'credit', 'contra_equity': 'debit',
    'revenue': 'credit', 'contra_revenue': 'debit',
    'cost_of_sales': 'debit', 'expense': 'debit',
    'other_income': 'credit', 'other_expense': 'debit',
}

# Each category is a section of a statement, in the order the statement shows them.
# Balance sheet: what the business owns = what it owes + what the owners have in it.
# Income statement: revenue − cost of sales = gross profit; − operating expenses =
# operating income; ± other income & expense = net income.
SECTIONS = {
    'cash': ('balance_sheet', 10),
    'receivables': ('balance_sheet', 20),
    'inventory': ('balance_sheet', 30),
    'other_current_assets': ('balance_sheet', 40),
    'fixed_assets': ('balance_sheet', 50),
    'current_liabilities': ('balance_sheet', 60),
    'long_term_liabilities': ('balance_sheet', 70),
    'equity': ('balance_sheet', 80),
    'revenue': ('income_statement', 10),
    'cost_of_sales': ('income_statement', 20),
    'operating_expenses': ('income_statement', 30),
    'other': ('income_statement', 40),
}

# Roles a posting can ask for. Each must be mapped in company config.gl_defaults.
ROLES = (
    'accounts_receivable',
    'other_receivables',
    'undeposited_funds',
    'inventory',
    'work_in_process',
    'accounts_payable',
    'labor_applied',
    'sales_tax_payable',
    'commission_payable',
    'retained_earnings',
    'sales_revenue',
    'shipping_revenue',
    'other_income',
    'finance_charge_income',
    'discount_given',
    'small_balance_writeoff',
    'bad_debt_writeoff',
    'cost_of_goods_sold',
    'inventory_cost_variance',
    'labor_variance',
    'scrap',
    'commission_expense',
    'default_expense',
    'fx_gain_loss',
)


class UndefinedAccountError(ValidationError):
    """An account code that is not an active account in the chart."""


def require_account(code: Optional[str], *, used_by: str = ''):
    """Return the active GlAccount for code, or raise UndefinedAccountError.

    used_by names the caller ("invoice 1023-inv tax", "item AF-2011 gls.revenue")
    so the error says where the bad code came from.
    """
    where = f' (used by {used_by})' if used_by else ''
    if not code or not isinstance(code, str):
        raise UndefinedAccountError(f'No GL account given{where}.')
    GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    account = GlAccount.objects.filter(ida=code).first()
    if account is None:
        raise UndefinedAccountError(
            f'GL account "{code}" is not in the chart of accounts{where}. '
            f'Add it to the chart or use a defined account.')
    if not account.is_active:
        raise UndefinedAccountError(f'GL account "{code}" is inactive{where}.')
    return account


def require_accounts(codes: Iterable[tuple[str, Optional[str]]]) -> None:
    """Check several (used_by, code) pairs; report every bad one at once."""
    errors = []
    for used_by, code in codes:
        try:
            require_account(code, used_by=used_by)
        except UndefinedAccountError as exc:
            errors.extend(exc.messages)
    if errors:
        raise UndefinedAccountError(errors)


def _mapped_code(role: str) -> str:
    """The code the company profile maps to this role, or ''."""
    Setting = dj_apps.get_model('core', 'Setting')
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    config = company.config if company and isinstance(company.config, dict) else {}
    defaults = config.get('gl_defaults') if isinstance(config.get('gl_defaults'), dict) else {}
    return defaults.get(role) or ''


def role_account(role: str, *, used_by: str = '', required: bool = True) -> str:
    """The account code the company assigns to a posting role.

    Reads company profile config.gl_defaults.{role}; the code must be in the chart.
    required=False returns '' when the role is not mapped (for filling blank
    defaults on a new record); a mapped code that is not in the chart still raises.

    An installation with no role map at all has not done anything wrong — it has
    not been given one yet. Before reporting an unmapped role, ask WC_HQ for the
    current recommended set and look again. The recommendation only ever fills
    roles the company left blank; a role the company mapped is never touched.
    """
    if role not in ROLES:
        raise UndefinedAccountError(f'Unknown GL role "{role}". Known roles: {", ".join(ROLES)}.')

    code = _mapped_code(role)
    if not code:
        from apps.core.services.installation_init import ensure_defined
        if ensure_defined('gl_defaults'):
            code = _mapped_code(role)

    if not code:
        if not required:
            return ''
        raise UndefinedAccountError(
            f'Company profile has no GL account for role "{role}" (config.gl_defaults.{role})'
            f'{" — needed by " + used_by if used_by else ""}.')
    require_account(code, used_by=f'company gl_defaults.{role}' + (f' for {used_by}' if used_by else ''))
    return code


def validate_gl_map(gl_map, *, owner: str) -> None:
    """Every non-empty string value in a {key: account code} map must be in the chart."""
    if not isinstance(gl_map, dict):
        return
    require_accounts(
        (f'{owner}.{key}', value)
        for key, value in gl_map.items()
        if isinstance(value, str) and value.strip()
    )


# ── Moving an account's references ───────────────────────────────────

# Where an account code is stored as a plain string field.
_CODE_FIELDS = (
    ('accounts', 'GlJournal', ('account',)),
    ('accounts', 'GlAccount', ('account_debit', 'account_credit')),
    ('accounts', 'Budget', ('account_debit', 'account_credit')),
    ('accounts', 'TaxJurisdiction', ('gl_account_payable',)),
)
# Where it sits somewhere inside a JSON envelope: an item's gls, an org's gl_accounts,
# the company's gl_defaults and commission accounts, cash methods, an invoice's
# finance.tax_gl_account.
_JSON_FIELDS = (
    ('products', 'Item', 'gls'),
    ('orgs', 'OrgBase', 'gl_accounts'),
    ('core', 'Setting', 'config'),
    ('transactions', 'Invoice', 'finance'),
)


def _swap(value, old: str, new: str):
    if isinstance(value, dict):
        return {k: _swap(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [_swap(v, old, new) for v in value]
    return new if value == old else value


def move_account_references(old: str, new: str) -> dict:
    """Point everything that names account ``old`` at ``new``. Returns {store: rows moved}.

    For renumbering or merging accounts. ``new`` must already be in the chart. The
    rows are updated directly (queryset.update): this re-points a code, it does not
    edit the record, so no save hook, version bump or recomputation should fire.
    """
    from django.db import transaction
    require_account(new, used_by=f'replacement for {old}')
    moved = {}
    with transaction.atomic():
        for app, model, fields in _CODE_FIELDS:
            Model = dj_apps.get_model(app, model)
            for field in fields:
                n = Model.objects.filter(**{field: old}).update(**{field: new})
                if n:
                    moved[f'{model}.{field}'] = n
        for app, model, field in _JSON_FIELDS:
            Model = dj_apps.get_model(app, model)
            n = 0
            for pk, value in Model.objects.exclude(**{f'{field}__isnull': True}).values_list('pk', field).iterator():
                if old in str(value):
                    swapped = _swap(value, old, new)
                    if swapped != value:
                        Model.objects.filter(pk=pk).update(**{field: swapped})
                        n += 1
            if n:
                moved[f'{model}.{field}'] = n
    return moved
