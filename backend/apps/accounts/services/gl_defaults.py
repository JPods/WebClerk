from __future__ import annotations

from typing import Iterable, Optional

from django.apps import apps as dj_apps


FALLBACK_DEFAULTS = {
    # Generic fallback GL ida values (can be overridden by org.gl_accounts)
    'revenue': '4000-Sales',
    'inventory': '1200-Inventory',
    'cogs': '5000-COGS',
    'purchase': '2000-AP',
    'commission': '6100-Commission',
    'tax_payable': '2100-SalesTax',
}


ROLE_ACTIVITY_DEFAULTS = {
    'rep': ('commission', 'expense', 'cogs'),
    'vendor': ('purchase', 'payables', 'expense'),
    'manufacturer': ('purchase', 'payables', 'expense'),
    'employee': ('commission', 'expense', 'cogs'),
}


def _pick_code(source: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_org_defaults(org: Optional[object]) -> dict:
    if org is not None:
        # OrgBase stores defaults under top-level gl_accounts JSON
        return (getattr(org, 'gl_accounts', None) or {}) or {}
    return {}


def _resolve_default(purpose: str, org_defaults: dict) -> Optional[str]:
    # Prefer org default, then global fallback
    if org_defaults and purpose in org_defaults:
        return org_defaults[purpose]
    return FALLBACK_DEFAULTS.get(purpose)


def get_default_ida_for_usage(*used_for_aliases: str) -> Optional[str]:
    """Return an active GL ida by used_for alias, if configured."""
    try:
        GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    except Exception:
        return None

    for alias in used_for_aliases:
        if not alias:
            continue
        account = (
            GlAccount.objects.filter(
                used_for__iexact=alias,
                is_active=True,
                is_deleted=False,
                is_archived=False,
            )
            .exclude(ida__isnull=True)
            .exclude(ida='')
            .first()
        )
        if account and account.ida:
            return account.ida
    return None


def get_item_gl_defaults() -> dict[str, str]:
    """Resolve default item GL mapping with primary_organization override.

    Priority:
    1) primary_organization setting data.default_gl_accounts / data.gl_accounts
    2) FALLBACK_DEFAULTS
    """
    defaults: dict[str, str] = {
        'revenue': FALLBACK_DEFAULTS.get('revenue', ''),
        'inventory': FALLBACK_DEFAULTS.get('inventory', ''),
        'cogs': FALLBACK_DEFAULTS.get('cogs', ''),
        'purchase': FALLBACK_DEFAULTS.get('purchase', ''),
    }

    try:
        from apps.orgs.services.primary_org import get_primary_org_setting

        setting = get_primary_org_setting()
        setting_data = setting.config if setting and isinstance(setting.config, dict) else {}
        primary_accounts = setting_data.get('default_gl_accounts') or setting_data.get('gl_accounts') or {}
        if isinstance(primary_accounts, dict):
            revenue = _pick_code(primary_accounts, 'revenue', 'sales')
            inventory = _pick_code(primary_accounts, 'inventory')
            cogs = _pick_code(primary_accounts, 'cogs', 'cost', 'expense')
            purchase = _pick_code(primary_accounts, 'purchase', 'payables', 'accounts_payable')
            variance = _pick_code(primary_accounts, 'variance')

            if revenue:
                defaults['revenue'] = revenue
            if inventory:
                defaults['inventory'] = inventory
            if cogs:
                defaults['cogs'] = cogs
            if purchase:
                defaults['purchase'] = purchase
            if variance:
                defaults['variance'] = variance
    except Exception:
        # Keep fallback defaults when settings are unavailable.
        pass

    if not defaults.get('variance') and defaults.get('cogs'):
        defaults['variance'] = defaults['cogs']

    return {k: v for k, v in defaults.items() if isinstance(v, str) and v}


def get_org_role_gl_defaults(org_type: str | None) -> dict[str, str]:
    """Resolve default org.gl_accounts values for role-based org records."""
    normalized = (org_type or '').lower().strip()
    if normalized not in ROLE_ACTIVITY_DEFAULTS:
        return {}

    defaults = dict(FALLBACK_DEFAULTS)
    activity_aliases = ROLE_ACTIVITY_DEFAULTS[normalized]
    activity = get_default_ida_for_usage(*activity_aliases)
    if not activity:
        for alias in activity_aliases:
            activity = defaults.get(alias)
            if activity:
                break

    result: dict[str, str] = {}
    if activity:
        result['activity'] = activity

    if normalized == 'rep':
        result['commission'] = (
            get_default_ida_for_usage('commission', 'expense')
            or defaults.get('commission')
            or activity
            or ''
        )
    elif normalized in {'vendor', 'manufacturer'}:
        result['purchase'] = (
            get_default_ida_for_usage('payables', 'expense')
            or defaults.get('purchase')
            or activity
            or ''
        )
    elif normalized == 'employee':
        result['expense'] = (
            get_default_ida_for_usage('expense', 'cogs')
            or defaults.get('cogs')
            or activity
            or ''
        )

    return {k: v for k, v in result.items() if v}


def get_invoice_payment_staging_defaults(payment_method_name: str | None = None, payment_method_metadata: dict | None = None) -> dict[str, str]:
    """Resolve GL account numbers used for invoice/payment staging metadata."""
    item_defaults = get_item_gl_defaults()
    revenue = item_defaults.get('revenue') or get_default_ida_for_usage('sales', 'revenue') or FALLBACK_DEFAULTS.get('revenue') or ''
    ar = get_default_ida_for_usage('receivables') or FALLBACK_DEFAULTS.get('receivables') or '1100-AR'

    method_gls = {}
    if isinstance(payment_method_metadata, dict):
        method_gls = payment_method_metadata.get('gl_accounts') or {}
        if not isinstance(method_gls, dict):
            method_gls = {}

    cash_receipt = method_gls.get('receipt') if isinstance(method_gls.get('receipt'), str) else None
    if not cash_receipt:
        cash_receipt = get_default_ida_for_usage('cash')
    if not cash_receipt:
        lowered_name = (payment_method_name or '').lower()
        cash_receipt = FALLBACK_DEFAULTS.get('cash' if 'cash' in lowered_name else 'receivables')
    if not cash_receipt:
        cash_receipt = '1000-Cash'

    return {
        'accounts_receivable': ar,
        'sales_revenue': revenue,
        'cash_receipt': cash_receipt,
    }


def assign_gl_defaults(obj, *, model_name: Optional[str] = None, purposes: Iterable[str] = ()):  # pragma: no cover
    """Assign default GL accounts onto an object if missing.

    Inputs:
      - obj: model instance (Item/Service, TaxJurisdiction, Contact, etc.)
    - model_name: explicit model hint (plural collection key, e.g., 'items', 'services', 'contacts', 'tax_jurisdictions')
      - purposes: iterable of purposes (e.g., 'sales','inventory','cost','purchase','commission','tax_payable')

    Behavior:
      - For Items/Services: writes into obj.gls JSON keys: revenue, inventory, cogs, purchase.
      - For TaxJurisdiction: writes gl_account_payable for 'tax_payable'.
      - For Contacts (commission recipients): writes obj.prefs.gl_accounts.commission.
      - No-ops when target key already set (non-empty).
    """
    # Attempt to locate an org from the object, if available (for org-specific defaults)
    org = getattr(obj, 'org', None) or getattr(obj, 'organization', None)
    org_defaults = _get_org_defaults(org)

    # Normalize model_name from model when not provided
    if not model_name:
        try:
            model_name = obj._meta.db_table
        except Exception:
            model_name = obj.__class__.__name__.lower()

    t = (model_name or '').lower()
    wanted = set([p.lower() for p in purposes])
    changed = 0

    if t in {'items', 'services'} or obj.__class__.__name__ == 'Item':
        gls = getattr(obj, 'gls', None) or {}
        if 'sales' in wanted:
            val = _resolve_default('revenue', org_defaults)
            if val and not gls.get('revenue'):
                gls['revenue'] = val; changed += 1
        if 'inventory' in wanted:
            val = _resolve_default('inventory', org_defaults)
            if val and not gls.get('inventory'):
                gls['inventory'] = val; changed += 1
        if 'cost' in wanted:
            val = _resolve_default('cogs', org_defaults)
            if val and not gls.get('cogs'):
                gls['cogs'] = val; changed += 1
        if 'purchase' in wanted:
            val = _resolve_default('purchase', org_defaults)
            if val and not gls.get('purchase'):
                gls['purchase'] = val; changed += 1
        if changed:
            setattr(obj, 'gls', gls)
        return changed

    if t in {'tax_jurisdictions'} or obj.__class__.__name__ == 'TaxJurisdiction':
        if 'tax_payable' in wanted:
            val = _resolve_default('tax_payable', org_defaults)
            if val and not getattr(obj, 'gl_account_payable', None):
                setattr(obj, 'gl_account_payable', val)
                changed += 1
        return changed

    # Contacts (commissions)
    Contact = dj_apps.get_model('core', 'Contact')
    if isinstance(obj, Contact) or t in {'contacts'}:
        if 'commission' in wanted:
            prefs = getattr(obj, 'prefs', None) or {}
            ga = prefs.get('gl_accounts') or {}
            if not ga.get('commission'):
                val = _resolve_default('commission', org_defaults)
                if val:
                    ga['commission'] = val
                    prefs['gl_accounts'] = ga
                    setattr(obj, 'prefs', prefs)
                    changed += 1
        return changed

    return 0


class GLDefaultsMixin:
    """Mixin to provide a helper for assigning GL defaults on models.

    Usage:
        class SomeModel(GLDefaultsMixin, BaseModel):
            ...
            def ensure_gl_defaults(self):
                return self.assign_gl_defaults(model_name='items', purposes=['sales','inventory','cost','purchase'])
    """

    def assign_gl_defaults(self, *, model_name: Optional[str] = None, purposes: Iterable[str] = ()):  # pragma: no cover
        return assign_gl_defaults(self, model_name=model_name, purposes=purposes)
