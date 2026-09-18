"""Default GL accounts for new records and staged postings.

Every default comes from the company role map (company profile
config.gl_defaults), resolved and checked against the chart by
apps.accounts.services.chart. There is no hard-coded fallback account: an
unmapped role leaves the field blank, and a posting that needs it fails.
"""
from __future__ import annotations

from typing import Iterable, Optional

from apps.accounts.services.chart import role_account

# Item gls key -> posting role
ITEM_GL_ROLES = {
    'revenue': 'sales_revenue',
    'inventory': 'inventory',
    'cogs': 'cost_of_goods_sold',
    'purchase': 'accounts_payable',
    'variance': 'cost_of_goods_sold',
}

# Org type -> {org gl_accounts key: posting role}
ORG_GL_ROLES = {
    'rep': {'activity': 'commission_expense', 'commission': 'commission_expense'},
    'employee': {'activity': 'default_expense', 'expense': 'default_expense'},
    'vendor': {'activity': 'accounts_payable', 'purchase': 'accounts_payable'},
    'manufacturer': {'activity': 'accounts_payable', 'purchase': 'accounts_payable'},
}


def _roles_to_codes(role_map: dict, used_by: str) -> dict[str, str]:
    codes = {key: role_account(role, used_by=used_by, required=False) for key, role in role_map.items()}
    return {k: v for k, v in codes.items() if v}


def get_item_gl_defaults() -> dict[str, str]:
    """Default item.gls from the company role map."""
    return _roles_to_codes(ITEM_GL_ROLES, 'item gls defaults')


def get_org_role_gl_defaults(org_type: str | None) -> dict[str, str]:
    """Default org.gl_accounts for rep/employee/vendor/manufacturer orgs."""
    role_map = ORG_GL_ROLES.get((org_type or '').lower().strip())
    return _roles_to_codes(role_map, f'{org_type} org gl_accounts defaults') if role_map else {}


def get_invoice_cash_staging_defaults(cash_method_name: str | None = None, cash_method_metadata: dict | None = None) -> dict[str, str]:
    """Accounts for the staged (preview) invoice/cash postings in metadata.

    A cash method may name its own receipt account (metadata.gl_accounts.receipt);
    it is checked against the chart like any other code.
    """
    from apps.accounts.services.chart import require_account

    receipt = None
    if isinstance(cash_method_metadata, dict):
        gls = cash_method_metadata.get('gl_accounts')
        if isinstance(gls, dict) and isinstance(gls.get('receipt'), str) and gls['receipt'].strip():
            receipt = require_account(gls['receipt'].strip(), used_by=f'cash method {cash_method_name} gl_accounts.receipt').ida
    return {
        'accounts_receivable': role_account('accounts_receivable', used_by='staged invoice', required=False),
        'sales_revenue': role_account('sales_revenue', used_by='staged invoice', required=False),
        'cash_receipt': receipt or role_account('undeposited_funds', used_by='staged cash', required=False),
    }


def assign_gl_defaults(obj, *, model_name: Optional[str] = None, purposes: Iterable[str] = ()):  # pragma: no cover
    """Fill blank GL accounts on an item, tax jurisdiction, or commission contact
    from the company role map. Never overwrites a value already set."""
    wanted = {p.lower() for p in purposes}
    changed = 0
    t = (model_name or getattr(getattr(obj, '_meta', None), 'db_table', '') or obj.__class__.__name__).lower()
    name = obj.__class__.__name__

    if t in {'items', 'services', 'products_item'} or name == 'Item':
        gls = getattr(obj, 'gls', None) or {}
        for purpose, key in (('sales', 'revenue'), ('inventory', 'inventory'), ('cost', 'cogs'), ('purchase', 'purchase')):
            if purpose in wanted and not gls.get(key):
                code = role_account(ITEM_GL_ROLES[key], used_by=f'item {getattr(obj, "ida", "")}', required=False)
                if code:
                    gls[key] = code
                    changed += 1
        if changed:
            obj.gls = gls
        return changed

    if t in {'tax_jurisdictions'} or name == 'TaxJurisdiction':
        if 'tax_payable' in wanted and not getattr(obj, 'gl_account_payable', None):
            code = role_account('sales_tax_payable', used_by='tax jurisdiction', required=False)
            if code:
                obj.gl_account_payable = code
                changed += 1
        return changed

    if name == 'Contact' or t in {'contacts'}:
        if 'commission' in wanted:
            prefs = getattr(obj, 'prefs', None) or {}
            ga = prefs.get('gl_accounts') or {}
            if not ga.get('commission'):
                code = role_account('commission_expense', used_by='commission contact', required=False)
                if code:
                    ga['commission'] = code
                    prefs['gl_accounts'] = ga
                    obj.prefs = prefs
                    changed += 1
        return changed

    return 0


class GLDefaultsMixin:
    """Mixin: self.assign_gl_defaults(model_name='items', purposes=[...])."""

    def assign_gl_defaults(self, *, model_name: Optional[str] = None, purposes: Iterable[str] = ()):  # pragma: no cover
        return assign_gl_defaults(self, model_name=model_name, purposes=purposes)
