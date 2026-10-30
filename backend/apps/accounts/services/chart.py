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

import json
import re
from pathlib import Path
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
    'received_not_billed',
    'labor_applied',
    'sales_tax_payable',
    'commission_payable',
    'small_stings_payable',
    'retained_earnings',
    'opening_balance_equity',
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
    'small_sting_expense',
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


# ── The standard chart ───────────────────────────────────────────────
# One file per chart (Bill, 2026-10-30): apps/accounts/charts/<name>.json =
# {name, description, numbering, accounts: [{ida, name, type, category, used_for, summary}],
#  roles: {role: account code}}. It is loaded like any other bundle
# (bundle_import.run(..., load='chart')) and only into a new database — one with no chart.
# From then on the company changes its accounts in the chart and its roles in the company
# profile (config.gl_defaults); the file never touches them again.

CHARTS_DIR = Path(__file__).resolve().parents[1] / 'charts'


def standard_chart(name: str = 'standard') -> dict:
    """A shipped chart file, read."""
    path = CHARTS_DIR / f'{name}.json'
    if not path.exists():
        known = ', '.join(sorted(p.stem for p in CHARTS_DIR.glob('*.json')))
        raise ValueError(f'No chart "{name}" — the charts are: {known}.')
    return json.loads(path.read_text())


def chart_defects(chart: dict) -> list[str]:
    """Everything wrong with a chart file, all at once; [] when it can be installed."""
    if not isinstance(chart, dict):
        return ['a chart is {name, accounts: [...], roles: {...}}']
    accounts = chart.get('accounts') or []
    roles = chart.get('roles') or {}
    defects, codes = [], set()
    for n, acct in enumerate(accounts):
        code = acct.get('ida') if isinstance(acct, dict) else None
        if not isinstance(code, str) or not ACCOUNT_CODE_PATTERN.match(code):
            defects.append(f'account {n}: code {code!r} is not {{number}}-{{lowercase_words}}')
            continue
        if code in codes:
            defects.append(f'{code}: listed twice')
        codes.add(code)
        if acct.get('type') not in NORMAL_BALANCE:
            defects.append(f'{code}: type {acct.get("type")!r} is not one of {", ".join(NORMAL_BALANCE)}')
        if acct.get('category') not in SECTIONS:
            defects.append(f'{code}: category {acct.get("category")!r} is not one of {", ".join(SECTIONS)}')
        if not acct.get('name'):
            defects.append(f'{code}: no name')
    if not accounts:
        defects.append('the chart has no accounts')
    for role in ROLES:
        if role not in roles:
            defects.append(f'role {role}: not mapped')
        elif roles[role] not in codes:
            defects.append(f'role {role}: {roles[role]!r} is not an account in this chart')
    defects += [f'role {role}: not a posting role' for role in roles if role not in ROLES]
    return defects


def install(chart: dict) -> dict:
    """Build the chart and the company's role map from a chart file — in a new database only.

    Returns {gl_accounts: {created}, roles: {mapped}, errors: [...]}; on any error nothing is
    written. The bundle loader for load='chart' (apps/core/services/bundle_import.py).
    """
    from django.db import transaction
    from apps.core.services.comment_stamp import append_comment
    GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    Setting = dj_apps.get_model('core', 'Setting')

    def refused(*errors):
        return {'gl_accounts': {'created': 0}, 'roles': {'mapped': 0}, 'errors': list(errors)}

    if GlAccount.objects.exists():
        return refused('This database already has a chart of accounts. A chart file is loaded only '
                       'into a new database; change accounts in the chart and posting roles in the '
                       'company profile (config.gl_defaults).')
    defects = chart_defects(chart)
    if defects:
        return refused(*defects)
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    if company is None:
        return refused('No company profile to hold the role map: load the settings bundle first.')

    with transaction.atomic():
        for acct in chart['accounts']:
            account = GlAccount(ida=acct['ida'], name=acct['name'], type=acct['type'],
                                category=acct['category'], used_for=acct.get('used_for') or '',
                                is_active=True)
            if acct.get('summary'):
                append_comment(account, 'process', acct['summary'], source=f'chart {chart.get("name")}',
                               key='account_use')
            account.save()
        config = dict(company.config or {})
        config['gl_defaults'] = {'note': (config.get('gl_defaults') or {}).get('note') or
                                 'Which chart account each posting role uses. Every code must be '
                                 'an active GlAccount (apps/accounts/services/chart.py).',
                                 **chart['roles']}
        company.config = config
        company.save()
    return {'gl_accounts': {'created': len(chart['accounts'])},
            'roles': {'mapped': len(chart['roles'])}, 'errors': []}
