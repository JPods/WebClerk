from __future__ import annotations

from typing import Iterable, Optional

from django.apps import apps as dj_apps


FALLBACK_DEFAULTS = {
    # Generic fallback GL account numbers (can be overridden by org.gl_accounts)
    'revenue': '4000',
    'inventory': '1200',
    'cogs': '5000',
    'purchase': '1100',
    'commission': '5200',
    'tax_payable': '2100',
}


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

    if t in {'items', 'services'} or obj.__class__.__name__ in {'Item', 'Service'}:
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
