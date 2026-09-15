"""Settings health check — validates all required Setting records exist and are structurally sound.

Called at startup. If unhealthy, the app must not proceed — Settings are the operating system.

Usage:
    from apps.core.services.setting_health import check_settings_health

    report = check_settings_health()
    if not report['healthy']:
        # Block app, show bootstrap dialog
        ...
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Required system Settings (non-model) ────────────────────────────────
REQUIRED_SYSTEM_SETTINGS = [
    {'purpose': 'wc:company_profile', 'description': 'Installation identity and defaults'},
    {'purpose': 'wc:admin', 'description': 'Admin popup choice lists'},
    {'purpose': 'wc:system', 'description': 'System reference data (country master)'},
    {'purpose': 'wc:dd_card', 'description': 'Dashboard card definitions'},
]

# ── Required keys per purpose ───────────────────────────────────────────
# What must exist in config for the Setting to be considered healthy
REQUIRED_CONFIG_KEYS = {
    'wc:model': ['layout', 'access', 'schema'],
    'wc:company_profile': ['company', 'gl_defaults', 'tax'],
    'wc:admin': ['lists'],
    'wc:dd_card': ['cards', 'dashboards'],
}

# Required metadata keys (universal — every Setting must have these)
REQUIRED_METADATA_KEYS = [
    'history', 'flags', 'userdefined', 'images',
]

# Required prefs keys
REQUIRED_PREFS_KEYS = ['userdefined', 'tags', 'pinned', 'search']

# Required refs keys
REQUIRED_REFS_KEYS = ['keywords', 'tags', 'links']


def check_settings_health() -> dict[str, Any]:
    """Validate all required Settings exist and are structurally sound.

    Returns:
        {
            'healthy': bool,
            'total': int,
            'missing': [{'type': str, 'description': str}, ...],
            'corrupt': [{'id': int, 'ida': str, 'issues': [str]}, ...],
            'summary': str,
        }
    """
    from apps.core.models.setting import Setting
    from apps.core.constants.model_registry import MODEL_REGISTRY

    missing = []
    corrupt = []

    # ── Check system Settings ───────────────────────────────────────
    for req in REQUIRED_SYSTEM_SETTINGS:
        exists = Setting.objects.filter(
            purpose=req['purpose'], is_active=True,
        ).exists()
        if not exists:
            missing.append({
                'type': f"System Setting (purpose={req['purpose']})",
                'description': req['description'],
            })

    # ── Check wc:model Settings — one per registered model ──────────
    skip_keys = {'wc', 'gantt', 'databrowser', 'project_association'}
    registry_keys = {k for k in MODEL_REGISTRY if k not in skip_keys}

    model_settings = {}
    for s in Setting.objects.filter(purpose='wc:model', is_active=True):
        if s.parent_model:
            model_settings[s.parent_model] = s

    # Check for missing model Settings
    for key in sorted(registry_keys):
        meta = MODEL_REGISTRY[key]
        # Check by canonical key or by parent_model matching any registered key
        if key not in model_settings and meta.key not in model_settings:
            missing.append({
                'type': f"Model Setting (parent_model={key})",
                'description': f"wc:model for {meta.singular}",
            })

    # ── Structural health check on all Settings ─────────────────────
    for s in Setting.objects.filter(is_active=True):
        issues = _check_record_health(s)
        if issues:
            corrupt.append({
                'id': s.id,
                'ida': s.ida or '',
                'purpose': s.purpose or '',
                'parent_model': s.parent_model or '',
                'issues': issues,
            })

    total = Setting.objects.filter(is_active=True).count()
    healthy = not missing and not corrupt

    summary_parts = []
    if healthy:
        summary_parts.append(f'All {total} Settings healthy.')
    else:
        if missing:
            summary_parts.append(f'{len(missing)} missing.')
        if corrupt:
            summary_parts.append(f'{len(corrupt)} corrupt.')
        summary_parts.append(f'{total} total active Settings.')

    report = {
        'healthy': healthy,
        'total': total,
        'missing': missing,
        'corrupt': corrupt,
        'summary': ' '.join(summary_parts),
    }

    if not healthy:
        logger.warning('Settings health check FAILED: %s', report['summary'])
    else:
        logger.info('Settings health check passed: %s', report['summary'])

    return report


def _check_record_health(setting) -> list[str]:
    """Check structural health of a single Setting record.

    Returns list of issue descriptions. Empty list = healthy.
    """
    issues = []

    # metadata structure
    if not isinstance(setting.metadata, dict):
        issues.append('metadata is not a dict')
    else:
        for key in REQUIRED_METADATA_KEYS:
            if key not in setting.metadata:
                issues.append(f'metadata missing: {key}')

    # prefs structure
    if not isinstance(setting.prefs, dict):
        issues.append('prefs is not a dict')
    else:
        for key in REQUIRED_PREFS_KEYS:
            if key not in setting.prefs:
                issues.append(f'prefs missing: {key}')

    # refs structure
    if not isinstance(setting.refs, dict):
        issues.append('refs is not a dict')
    else:
        for key in REQUIRED_REFS_KEYS:
            if key not in setting.refs:
                issues.append(f'refs missing: {key}')

    # config structure — purpose-specific
    purpose = setting.purpose or ''
    required_keys = REQUIRED_CONFIG_KEYS.get(purpose, [])
    if required_keys:
        if not isinstance(setting.config, dict):
            issues.append('config is not a dict')
        else:
            for key in required_keys:
                if key not in setting.config:
                    issues.append(f'config missing: {key}')

    # explanation — tracked separately as advisory; not a structural issue.
    # WC_HQ enforces explanations before sync acceptance.

    return issues
