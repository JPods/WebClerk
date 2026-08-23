"""App bootstrap service — single endpoint returns all startup data for React.

Nothing hardcoded in React. All defaults, select lists, company info,
payment terms, tax jurisdictions, warehouses, and campaigns come from here.

Called once at app startup and on manual refresh. React caches 5 minutes.
"""
from __future__ import annotations

from django.apps import apps as dj_apps


def get_bootstrap_dt() -> int:
    """Return the timestamp of last admin change to defaults/lists/config.

    React checks this on a lightweight poll. If it's newer than the cached
    dt, React calls get_app_bootstrap() to refresh.

    Updated by touch_bootstrap() whenever an admin changes defaults,
    select lists, company profile, terms, jurisdictions, etc.
    """
    Setting = dj_apps.get_model('core', 'Setting')
    try:
        s = Setting.objects.filter(purpose='wc:db_defaults', parent_model='setting', name='bootstrap_version').first()
        if s and isinstance(s.config, dict):
            return s.config.get('dt_changed', 0)
    except Exception:
        pass
    return 0


def touch_bootstrap() -> int:
    """Stamp the bootstrap with current time. Call after any admin change.

    React polls get_bootstrap_dt() and refreshes when dt_changed is newer
    than what it has cached.
    """
    import time
    Setting = dj_apps.get_model('core', 'Setting')
    now_ms = int(time.time() * 1000)
    s, _ = Setting.objects.get_or_create(
        purpose='wc:db_defaults', parent_model='setting', name='bootstrap_version',
        defaults={'ida': 'bootstrap-dt', 'config': {'dt_changed': now_ms}},
    )
    config = s.config or {}
    config['dt_changed'] = now_ms
    s.config = config
    s.save(update_fields=['config'])
    return now_ms


def get_app_bootstrap() -> dict:
    """Gather all startup data React needs in one call.

    Returns:
        {company, select_lists, payment_terms, tax_jurisdictions,
         warehouses, campaigns, defaults, dt_changed}
    """
    return {
        'dt_changed': get_bootstrap_dt(),
        'company': _get_company_profile(),
        'select_lists': _get_select_lists(),
        'payment_terms': _get_payment_terms(),
        'tax_jurisdictions': _get_tax_jurisdictions(),
        'warehouses': _get_warehouses(),
        'campaigns': _get_campaigns(),
        'defaults': _get_defaults(),
    }


def _get_company_profile() -> dict:
    """Company name, address, logos from Setting purpose='wc:company_profile'."""
    Setting = dj_apps.get_model('core', 'Setting')
    try:
        s = Setting.objects.filter(purpose='wc:company_profile').first()
        if s and isinstance(s.config, dict):
            c = s.config
            return {
                'name': c.get('company', {}).get('name', ''),
                'legal_name': c.get('company', {}).get('legal_name', ''),
                'address': c.get('company', {}).get('address', {}),
                'phone': c.get('company', {}).get('phone', ''),
                'email': c.get('company', {}).get('email', ''),
                'website': c.get('company', {}).get('website', ''),
                'tax_id': c.get('company', {}).get('tax_id', ''),
                'logos': c.get('logos', {}),
            }
    except Exception:
        pass
    return {}


def _get_select_lists() -> dict:
    """All select lists from Setting purpose='wc:selectlist'."""
    Setting = dj_apps.get_model('core', 'Setting')
    lists = {}
    try:
        settings = Setting.objects.filter(purpose='wc:selectlist', is_active=True)
        for s in settings:
            config = s.config or {}
            for key, options in config.items():
                if isinstance(options, list):
                    # Normalize to [{value, label}]
                    normalized = []
                    for opt in options:
                        if isinstance(opt, dict):
                            normalized.append({'value': str(opt.get('value', '')), 'label': str(opt.get('label', opt.get('value', '')))})
                        elif isinstance(opt, (list, tuple)) and len(opt) >= 2:
                            normalized.append({'value': str(opt[0]), 'label': str(opt[1])})
                        elif isinstance(opt, str):
                            normalized.append({'value': opt, 'label': opt})
                    lists[key] = normalized
    except Exception:
        pass
    return lists


def _get_payment_terms() -> list:
    """Active payment terms for dropdowns."""
    Term = dj_apps.get_model('accounts', 'Term')
    try:
        return list(
            Term.objects.filter(is_active=True)
            .values('id', 'description', 'days_due', 'period_count', 'days_discount', 'discount_rate')
            .order_by('description')
        )
    except Exception:
        return []


def _get_tax_jurisdictions() -> list:
    """Active tax jurisdictions for dropdowns."""
    TaxJurisdiction = dj_apps.get_model('accounts', 'TaxJurisdiction')
    try:
        return [
            {'id': tj.pk, 'jurisdiction': tj.tax_jurisdiction or '', 'rate': tj.tax_rate_sales or 0,
             'name': tj.tax_name or '', 'on_shipping': tj.tax_rate_on_shipping or 0}
            for tj in TaxJurisdiction.objects.filter(is_active=True).order_by('tax_jurisdiction')
        ]
    except Exception:
        return []


def _get_warehouses() -> list:
    """Active warehouses for location dropdowns."""
    Warehouse = dj_apps.get_model('products', 'Warehouse')
    try:
        return list(
            Warehouse.objects.filter(is_active=True)
            .values('id', 'code', 'name', 'site_code')
            .order_by('code')
        )
    except Exception:
        return []


def _get_campaigns() -> list:
    """Active campaigns for source attribution dropdown."""
    # Campaign model may not exist yet (raw SQL → ORM migration pending)
    try:
        Setting = dj_apps.get_model('core', 'Setting')
        campaigns = Setting.objects.filter(purpose='user:campaign', is_active=True).values('id', 'name')
        return list(campaigns)
    except Exception:
        return []


def _get_defaults() -> dict:
    """Default values from Setting purpose='wc:db_defaults'."""
    Setting = dj_apps.get_model('core', 'Setting')
    defaults = {}
    try:
        settings = Setting.objects.filter(purpose='wc:db_defaults', is_active=True)
        for s in settings:
            if isinstance(s.config, dict):
                defaults.update(s.config)
    except Exception:
        pass
    return defaults
