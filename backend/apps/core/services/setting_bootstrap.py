"""Settings bootstrap — fetch or import Settings when health check fails.

Two sources:
    1. Git bundle — user pulls settings-bundle.json from repo, uploads it
    2. WC_HQ API — fetch from webclerk.com/wcapi/settings-bundle/

WC_HQ API requires an Athena token. The URL is always webclerk.com/... —
webclerk.com IS the path, not a parameter. No token, no fetch.

Usage (an import is recorded through apps/core/services/bundle_import.py):
    from apps.core.services import bundle_import
    from apps.core.services.setting_bootstrap import fetch_from_wchq

    # From a local file (git pull)
    result = bundle_import.run('settings', bundle_data, source='file', load='settings')

    # From WC_HQ (requires Athena token)
    result = fetch_from_wchq(athena_token)
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

WCHQ_SETTINGS_URL = 'https://webclerk.com/wcapi/settings-bundle/'


def _deep_merge_baseline(current: dict, incoming: dict) -> dict:
    """Merge incoming baseline into current — add missing keys, never replace existing.

    This is the core principle: WC_HQ provides the baseline structure.
    User customizations always win. New keys from HQ are added silently.
    """
    merged = dict(current)
    for key, value in incoming.items():
        if key not in merged:
            # Key missing from user's record — add from baseline
            merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            # Both are dicts — recurse
            merged[key] = _deep_merge_baseline(merged[key], value)
        # else: user has this key — leave it alone
    return merged


def _is_foundational(record) -> bool:
    """Check if a DB record is marked as foundational (from init bundle)."""
    meta = getattr(record, 'metadata', None) or {}
    return bool(meta.get('foundational'))


def import_settings_bundle(
    bundle_data: dict | list,
    force_foundational: bool = False,
    force_replace: bool = False,
) -> dict[str, Any]:
    """Import a settings bundle — create or update Setting records.

    The loop lives in apps/core/services/record_import.py, which every importer
    now shares. This keeps the Setting-specific entry point and its argument
    names, because callers and commands use them.

    force_replace: REPLACE existing config/metadata/refs instead of baseline
        merging. For restoring corrupted Settings from a known-good copy.
        Requires double confirmation at the command level. `prefs` is NEVER
        replaced — the user's sovereign space — in any mode.
    """
    from apps.core.services.record_import import import_records

    if isinstance(bundle_data, dict):
        records = bundle_data.get('settings', bundle_data.get('records', []))
    else:
        records = bundle_data

    if not isinstance(records, list):
        return {'created': 0, 'updated': 0, 'replaced': 0, 'protected': 0,
                'errors': ['bundle_data must contain a list of records']}

    return import_records(
        'core.Setting', records,
        match_on=('uuid',),
        authoritative=force_foundational,
        replace=force_replace,
    )


def fetch_from_wchq(athena_token: str) -> dict[str, Any]:
    """Fetch settings bundle from webclerk.com/wcapi/settings-bundle/.

    Requires a valid Athena token. No token = no fetch.
    webclerk.com IS the path — not configurable, not parameterized.

    Returns: {success: bool, created: int, updated: int, errors: [str]}
    """
    import requests

    if not athena_token:
        return {
            'success': False,
            'created': 0, 'updated': 0,
            'errors': ['Athena token required to fetch from WC_HQ'],
        }

    try:
        resp = requests.get(
            WCHQ_SETTINGS_URL,
            headers={
                'Authorization': f'Athena {athena_token}',
                'Accept': 'application/json',
            },
            timeout=30,
        )

        if resp.status_code == 401:
            return {
                'success': False,
                'created': 0, 'updated': 0,
                'errors': ['Athena token rejected by WC_HQ — unauthorized'],
            }

        if resp.status_code == 403:
            return {
                'success': False,
                'created': 0, 'updated': 0,
                'errors': ['Athena token valid but access denied — check permissions'],
            }

        if resp.status_code != 200:
            return {
                'success': False,
                'created': 0, 'updated': 0,
                'errors': [f'WC_HQ returned status {resp.status_code}'],
            }

        bundle_data = resp.json()
        from apps.core.services import bundle_import
        result = bundle_import.run('settings', bundle_data, source='wchq', load='settings')
        result['success'] = not result['errors']
        return result

    except requests.ConnectionError:
        return {
            'success': False,
            'created': 0, 'updated': 0,
            'errors': ['Cannot reach webclerk.com — check network connection'],
        }
    except Exception as e:
        logger.exception('settings_bootstrap: WC_HQ fetch failed')
        return {
            'success': False,
            'created': 0, 'updated': 0,
            'errors': [f'WC_HQ fetch failed: {e}'],
        }
