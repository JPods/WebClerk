"""The named bundles WC_HQ publishes, and what each one is for.

One entry per bundle. Each says three things:

    pack   what HQ puts in it          (run on webclerk.com)
    check  how an installation tells    (run on the installation)
           whether it already has it
    needs  which other bundles must
           land first

An installation that finds a definition set missing asks for the bundle that
carries it — ``/wcapi/get/bundle_gls.json`` and the rest — rather than pulling
the whole baseline to fix one blank field.

The GL bundle carries the chart *and* the role map together on purpose. A role
map pointing at accounts that do not exist is refused by
apps/accounts/services/chart.py, so shipping one without the other produces the
same blank field by a longer route.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

GL_ACCOUNT_FIELDS = (
    'name', 'type', 'category', 'description', 'explanation',
    'sort_order', 'security_level',
)


# ------------------------------------------------------------------- packing
# These run on WC_HQ. An installation never calls them.


def _serialize_setting(setting) -> dict | None:
    from apps.core.services.demo_bundle import sanitize_setting

    if not setting.uuid:
        return None
    return sanitize_setting({
        'uuid': str(setting.uuid),
        'ida': setting.ida or '',
        'name': setting.name or '',
        'scope': setting.scope or 'system',
        'purpose': setting.purpose or '',
        'parent_model': setting.parent_model or '',
        'explanation': getattr(setting, 'explanation', '') or '',
        'paths': getattr(setting, 'paths', {}) or {},
        'config': setting.config or {},
        'metadata': {**(setting.metadata or {}), 'foundational': True},
        'prefs': setting.prefs or {},
        'refs': setting.refs or {},
    })


def _serialize_report(report) -> dict | None:
    from apps.core.services.demo_bundle import scrub_emails

    if not report.uuid:
        return None
    return scrub_emails({
        'uuid': str(report.uuid),
        'ida': report.ida or '',
        'name': report.name or '',
        'description': report.description or '',
        'model_name': report.model_name or '',
        'purpose': report.purpose or '',
        'record_id': report.record_id or '',
        'output_type': report.output_type or '',
        'category': report.category or '',
        'role_required': report.role_required or '',
        'sort_order': report.sort_order or 0,
        'explanation': getattr(report, 'explanation', '') or '',
        'paths': getattr(report, 'paths', {}) or {},
        'config': report.config or {},
        'metadata': {**(report.metadata or {}), 'foundational': True},
        'prefs': report.prefs or {},
        'refs': report.refs or {},
        'editor_type': report.editor_type or '',
        'content': report.content or '',
    })


def _serialize_gl_account(account) -> dict | None:
    if not account.uuid:
        return None
    rec: dict[str, Any] = {'uuid': str(account.uuid), 'ida': account.ida or ''}
    for field in GL_ACCOUNT_FIELDS:
        rec[field] = getattr(account, field, None)
    rec['config'] = account.config or {}
    rec['metadata'] = {**(account.metadata or {}), 'foundational': True}
    return rec


def pack_settings() -> dict:
    from apps.core.models.setting import Setting
    from apps.core.services.demo_bundle import RUNTIME_SETTING_PURPOSES

    rows = (Setting.objects
            .filter(is_active=True)
            .exclude(purpose__in=RUNTIME_SETTING_PURPOSES)
            .order_by('purpose', 'parent_model'))
    return {'settings': [r for r in (_serialize_setting(s) for s in rows) if r]}


def pack_reports() -> dict:
    from django.apps import apps as dj_apps

    try:
        Report = dj_apps.get_model('core', 'Report')
    except LookupError:
        return {'reports': []}
    rows = Report.objects.filter(is_active=True).order_by('model_name', 'category', 'name')
    return {'reports': [r for r in (_serialize_report(x) for x in rows) if r]}


def pack_gls() -> dict:
    """The chart of accounts and the posting-role map that points into it."""
    from django.apps import apps as dj_apps

    from apps.core.models.setting import Setting

    accounts: list[dict] = []
    try:
        GlAccount = dj_apps.get_model('accounts', 'GlAccount')
        rows = GlAccount.objects.filter(is_active=True).order_by('ida')
        accounts = [r for r in (_serialize_gl_account(a) for a in rows) if r]
    except LookupError:
        logger.warning('[BUNDLE] GlAccount model not found — chart omitted')

    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    config = company.config if company and isinstance(company.config, dict) else {}
    gl_defaults = config.get('gl_defaults') if isinstance(config.get('gl_defaults'), dict) else {}

    # The role map travels as a settings record so it merges through the same
    # uuid-keyed baseline merge as everything else.
    settings: list[dict] = []
    if company and gl_defaults:
        rec = _serialize_setting(company)
        if rec:
            rec['config'] = {'gl_defaults': gl_defaults}
            settings.append(rec)

    return {'gl_accounts': accounts, 'settings': settings}


def pack_init() -> dict:
    """Everything a new database starts from."""
    bundle = {}
    bundle.update(pack_settings())
    bundle.update(pack_reports())
    bundle.update({'gl_accounts': pack_gls()['gl_accounts']})
    return bundle


# -------------------------------------------------------------------- checks
# These run on the installation.


def _has_gl_role_map() -> bool:
    from apps.core.models.setting import Setting

    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    config = company.config if company and isinstance(company.config, dict) else {}
    defaults = config.get('gl_defaults')
    if not isinstance(defaults, dict):
        return False
    return any(isinstance(v, str) and v.strip()
               for k, v in defaults.items() if k != 'note')


def _has_chart() -> bool:
    from django.apps import apps as dj_apps

    try:
        GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    except LookupError:
        return False
    return GlAccount.objects.filter(is_active=True).exists()


def _has_gls() -> bool:
    return _has_chart() and _has_gl_role_map()


def _has_executable_reports() -> bool:
    """Reports this installation can run — the record names an executor we have."""
    from apps.core.services.report_registry import EXECUTORS, REPORT_PURPOSE_EXECUTABLE
    from django.apps import apps as dj_apps

    try:
        Report = dj_apps.get_model('core', 'Report')
    except LookupError:
        return False
    return Report.objects.filter(
        purpose=REPORT_PURPOSE_EXECUTABLE, is_active=True,
        ida__in=list(EXECUTORS)).exists()


def _has_reports() -> bool:
    from django.apps import apps as dj_apps

    try:
        Report = dj_apps.get_model('core', 'Report')
    except LookupError:
        return False
    return Report.objects.filter(is_active=True).exists()


def _has_settings() -> bool:
    from apps.core.models.setting import Setting

    return Setting.objects.filter(is_active=True, purpose__startswith='wc:').exists()


BundlePack = Callable[[], dict]
BundleCheck = Callable[[], bool]


class BundleSpec:
    __slots__ = ('name', 'pack', 'check', 'description')

    def __init__(self, name: str, pack: BundlePack, check: BundleCheck, description: str):
        self.name = name
        self.pack = pack
        self.check = check
        self.description = description


CATALOGUE: dict[str, BundleSpec] = {
    'gls': BundleSpec(
        'gls', pack_gls, _has_gls,
        'chart of accounts and the posting-role map that points into it'),
    'reports': BundleSpec(
        'reports', pack_reports, _has_reports,
        'report, form, print and executable definitions'),
    'settings': BundleSpec(
        'settings', pack_settings, _has_settings,
        'layouts, select lists and system configuration'),
    'init': BundleSpec(
        'init', pack_init, lambda: _has_settings() and _has_reports(),
        'everything a new database starts from'),
}

# A definition set an installation can ask about -> the bundle that carries it.
DEFINITION_BUNDLES: dict[str, tuple[str, BundleCheck]] = {
    'gl_defaults': ('gls', _has_gl_role_map),
    'chart': ('gls', _has_chart),
    'gls': ('gls', _has_gls),
    'executable_reports': ('reports', _has_executable_reports),
    'reports': ('reports', _has_reports),
    'settings': ('settings', _has_settings),
}
