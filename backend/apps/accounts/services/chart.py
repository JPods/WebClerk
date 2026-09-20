"""Chart of accounts — the one authority for which GL accounts exist.

The GlAccount table is the chart. Every account code used anywhere — a journal
posting, an item's gls, an org's gl_accounts, a tax jurisdiction, the company
role defaults — must be an active GlAccount. Using any other code raises
UndefinedAccountError; nothing falls back to a guessed account.

Role defaults (which account an invoice's tax, freight, AR... post to) live in
the company profile Setting: config.gl_defaults.{role} = account code.

Code style: {4-digit number}-{lowercase_words}, e.g. 1100-accounts_receivable.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from django.apps import apps as dj_apps
from django.core.exceptions import ValidationError

ACCOUNT_CODE_PATTERN = re.compile(r'^\d{4}-[a-z0-9]+(?:_[a-z0-9]+)*$')

# Roles a posting can ask for. Each must be mapped in company config.gl_defaults.
ROLES = (
    'accounts_receivable',
    'other_receivables',
    'undeposited_funds',
    'inventory',
    'accounts_payable',
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
    account = GlAccount.objects.filter(ida=code, is_deleted=False).first()
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
