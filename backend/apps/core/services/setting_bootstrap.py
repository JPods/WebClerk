"""Settings bootstrap — fetch or import Settings when health check fails.

Two sources:
    1. Git bundle — user pulls settings-bundle.json from repo, uploads it
    2. WC_HQ API — fetch from webclerk.com/wcapi/settings-bundle/

WC_HQ API requires an Athena token. The URL is always webclerk.com/... —
webclerk.com IS the path, not a parameter. No token, no fetch.

Usage:
    from apps.core.services.setting_bootstrap import (
        import_settings_bundle,
        fetch_from_wchq,
    )

    # From a local file (git pull)
    result = import_settings_bundle(bundle_data)

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
        result = import_settings_bundle(bundle_data)
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


# ---------------------------------------------------------------------------
# Export — Alice's settings backup
# ---------------------------------------------------------------------------

SETTINGS_BACKUP_DIR = 'settings_backups'
SETTINGS_BACKUP_KEEP_DAYS = 7


def export_settings_bundle() -> dict[str, Any]:
    """Export all Setting records as a JSON bundle.

    Returns: {success: bool, path: str, count: int, size_bytes: int}
    """
    import os
    from datetime import datetime, timezone
    from django.conf import settings as django_settings
    from apps.core.models.setting import Setting

    records = []
    for s in Setting.objects.filter(is_active=True).order_by('purpose', 'parent_model'):
        records.append({
            'uuid': str(s.uuid) if s.uuid else None,
            'ida': s.ida or '',
            'name': s.name or '',
            'scope': s.scope or 'system',
            'purpose': s.purpose or '',
            'parent_model': s.parent_model or '',
            'explanation': s.explanation or '',
            'paths': s.paths if isinstance(s.paths, dict) else {},
            'config': s.config if isinstance(s.config, dict) else {},
            'metadata': s.metadata if isinstance(s.metadata, dict) else {},
            'prefs': s.prefs if isinstance(s.prefs, dict) else {},
            'refs': s.refs if isinstance(s.refs, dict) else {},
        })

    bundle = {
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'count': len(records),
        'settings': records,
    }

    # Write to backup directory (in DATA_DIR, outside the repo)
    data_dir = getattr(django_settings, 'DATA_DIR', None)
    base = str(data_dir) if data_dir else os.path.join(os.getcwd(), 'data')
    backup_dir = os.path.join(base, SETTINGS_BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f'settings-bundle-{ts}.json'
    filepath = os.path.join(backup_dir, filename)

    content = json.dumps(bundle, indent=2, default=str)
    with open(filepath, 'w') as f:
        f.write(content)

    logger.info('settings_backup: exported %d records to %s (%d bytes)',
                len(records), filepath, len(content))

    return {
        'success': True,
        'path': filepath,
        'filename': filename,
        'count': len(records),
        'size_bytes': len(content),
    }


def prune_old_backups() -> dict[str, Any]:
    """Remove settings backups older than SETTINGS_BACKUP_KEEP_DAYS.

    Returns: {pruned: int, kept: int}
    """
    import os
    from datetime import datetime, timezone, timedelta
    from django.conf import settings as django_settings

    data_dir = getattr(django_settings, 'DATA_DIR', None)
    base = str(data_dir) if data_dir else os.path.join(os.getcwd(), 'data')
    backup_dir = os.path.join(base, SETTINGS_BACKUP_DIR)

    if not os.path.exists(backup_dir):
        return {'pruned': 0, 'kept': 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=SETTINGS_BACKUP_KEEP_DAYS)
    pruned = 0
    kept = 0

    for filename in sorted(os.listdir(backup_dir)):
        if not filename.startswith('settings-bundle-') or not filename.endswith('.json'):
            continue
        filepath = os.path.join(backup_dir, filename)
        # Parse date from filename: settings-bundle-YYYY-MM-DD.json
        try:
            date_str = filename.replace('settings-bundle-', '').replace('.json', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if file_date < cutoff:
                os.remove(filepath)
                pruned += 1
                logger.info('settings_backup: pruned %s', filename)
            else:
                kept += 1
        except (ValueError, OSError) as e:
            logger.warning('settings_backup: could not process %s: %s', filename, e)
            kept += 1

    return {'pruned': pruned, 'kept': kept}


# ---------------------------------------------------------------------------
# Report backup — same pattern as Settings
# ---------------------------------------------------------------------------

REPORT_BACKUP_DIR = 'report_backups'
REPORT_BACKUP_KEEP_DAYS = 7


def export_report_bundle() -> dict[str, Any]:
    """Export all Report records as a JSON bundle.

    Reports are user-created configuration — form templates, print layouts,
    dashboard definitions. As consequential as Settings, different cadence.
    """
    import os
    from datetime import datetime, timezone
    from django.conf import settings as django_settings
    from apps.core.models import Report

    records = []
    for r in Report.objects.filter(is_active=True).order_by('category', 'model_name'):
        records.append({
            'uuid': str(r.uuid) if r.uuid else None,
            'ida': r.ida or '',
            'name': r.name or '',
            'description': r.description or '',
            'model_name': r.model_name or '',
            'category': r.category or '',
            'output_type': r.output_type or '',
            'role_required': r.role_required or '',
            'sort_order': r.sort_order,
            'editor_type': r.editor_type or '',
            'explanation': r.explanation or '',
            'paths': r.paths if isinstance(r.paths, dict) else {},
            'config': r.config if isinstance(r.config, dict) else {},
            'metadata': r.metadata if isinstance(r.metadata, dict) else {},
            'prefs': r.prefs if isinstance(r.prefs, dict) else {},
            'refs': r.refs if isinstance(r.refs, dict) else {},
            'content': r.content or '',
        })

    bundle = {
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'count': len(records),
        'reports': records,
    }

    data_dir = getattr(django_settings, 'DATA_DIR', None)
    base = str(data_dir) if data_dir else os.path.join(os.getcwd(), 'data')
    backup_dir = os.path.join(base, REPORT_BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f'report-bundle-{ts}.json'
    filepath = os.path.join(backup_dir, filename)

    content = json.dumps(bundle, indent=2, default=str)
    with open(filepath, 'w') as f:
        f.write(content)

    logger.info('report_backup: exported %d records to %s (%d bytes)',
                len(records), filepath, len(content))

    return {
        'success': True,
        'path': filepath,
        'filename': filename,
        'count': len(records),
        'size_bytes': len(content),
    }


def prune_old_report_backups() -> dict[str, Any]:
    """Remove report backups older than REPORT_BACKUP_KEEP_DAYS."""
    import os
    from datetime import datetime, timezone, timedelta
    from django.conf import settings as django_settings

    data_dir = getattr(django_settings, 'DATA_DIR', None)
    base = str(data_dir) if data_dir else os.path.join(os.getcwd(), 'data')
    backup_dir = os.path.join(base, REPORT_BACKUP_DIR)

    if not os.path.exists(backup_dir):
        return {'pruned': 0, 'kept': 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=REPORT_BACKUP_KEEP_DAYS)
    pruned = 0
    kept = 0

    for filename in sorted(os.listdir(backup_dir)):
        if not filename.startswith('report-bundle-') or not filename.endswith('.json'):
            continue
        filepath = os.path.join(backup_dir, filename)
        try:
            date_str = filename.replace('report-bundle-', '').replace('.json', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if file_date < cutoff:
                os.remove(filepath)
                pruned += 1
                logger.info('report_backup: pruned %s', filename)
            else:
                kept += 1
        except (ValueError, OSError) as e:
            logger.warning('report_backup: could not process %s: %s', filename, e)
            kept += 1

    return {'pruned': pruned, 'kept': kept}
