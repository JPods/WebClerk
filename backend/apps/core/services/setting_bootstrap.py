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

    bundle_data: list of Setting dicts, each with at least:
        uuid, ida, purpose, parent_model, config, metadata, prefs, refs,
        explanation, paths, scope, name

    UUID controls merge: if a Setting with matching UUID exists, update it.
    If not, create it.

    force_replace: if True, REPLACE existing config/metadata/refs instead of
        baseline merge. Used when Settings are corrupted and must be restored
        to a known-good state. Requires double confirmation at the command level.
        Prefs are NEVER replaced (user's sovereign space).

    Foundational protection: records with metadata.foundational=true in the
    database are NEVER modified by external bundles. Only unpack_init_bundle
    (which passes force_foundational=True) can update them.

    Returns: {created: int, updated: int, replaced: int, protected: int, errors: [str]}
    """
    from apps.core.models.setting import Setting

    if isinstance(bundle_data, dict):
        records = bundle_data.get('settings', bundle_data.get('records', []))
    else:
        records = bundle_data

    if not isinstance(records, list):
        return {'created': 0, 'updated': 0, 'protected': 0,
                'errors': ['bundle_data must contain a list of records']}

    created = 0
    updated = 0
    replaced = 0
    protected = 0
    errors = []

    for rec in records:
        try:
            uuid_val = rec.get('uuid')
            if not uuid_val:
                errors.append(f"Record missing uuid: ida={rec.get('ida', '?')}")
                continue

            existing = Setting.objects.filter(uuid=uuid_val).first()

            if existing:
                # Foundational protection — skip unless this is the init bundle
                if _is_foundational(existing) and not force_foundational:
                    protected += 1
                    continue

                if force_replace:
                    # REPLACE mode — overwrite config/metadata/refs entirely.
                    # Used when Settings are corrupted and must be restored.
                    # Prefs are NEVER replaced (user's sovereign space).
                    for field in ('name', 'scope', 'purpose', 'parent_model'):
                        if field in rec:
                            setattr(existing, field, rec[field])
                    existing.explanation = rec.get('explanation', '')
                    existing.paths = rec.get('paths', {})
                    for field in ('config', 'metadata', 'refs'):
                        if field in rec:
                            setattr(existing, field, rec[field] or {})
                    # prefs — NEVER replaced, even in replace mode
                    existing._setting_update_authorized = True
                    existing.save()
                    replaced += 1
                else:
                    # BASELINE MERGE — add missing keys, never replace existing.
                    # WC_HQ settings are the baseline. User customizations win.

                    # Scalar fields — only update if currently empty
                    for field in ('name', 'scope', 'purpose', 'parent_model'):
                        if field in rec and not getattr(existing, field, None):
                            setattr(existing, field, rec[field])

                    # explanation/paths — update if empty
                    if not getattr(existing, 'explanation', ''):
                        existing.explanation = rec.get('explanation', '')
                    if not getattr(existing, 'paths', None):
                        existing.paths = rec.get('paths', {})

                    # JSON fields — deep merge: add missing keys, preserve existing
                    for field in ('config', 'metadata', 'refs'):
                        if field in rec:
                            current = getattr(existing, field, None) or {}
                            incoming = rec[field] or {}
                            merged = _deep_merge_baseline(current, incoming)
                            setattr(existing, field, merged)

                    # prefs — never touch (user's space)
                    existing._setting_update_authorized = True
                    existing.save()
                    updated += 1
            else:
                # Create — new records bypass the wall (no existing config to protect)
                s = Setting(
                    uuid=uuid_val,
                    ida=rec.get('ida', ''),
                    name=rec.get('name', ''),
                    scope=rec.get('scope', 'system'),
                    purpose=rec.get('purpose', ''),
                    parent_model=rec.get('parent_model'),
                    explanation=rec.get('explanation', ''),
                    paths=rec.get('paths', {}),
                    config=rec.get('config', {}),
                    metadata=rec.get('metadata', {}),
                    prefs=rec.get('prefs', {}),
                    refs=rec.get('refs', {}),
                )
                s._setting_update_authorized = True  # approved bootstrap path
                s.save()
                created += 1

        except Exception as e:
            errors.append(f"Error on ida={rec.get('ida', '?')}: {e}")
            logger.exception('settings_bootstrap: import error')

    if protected:
        logger.info('settings_bootstrap: %d foundational records protected from external bundle', protected)
    logger.info('settings_bootstrap: created=%d updated=%d replaced=%d protected=%d errors=%d',
                created, updated, replaced, protected, len(errors))
    return {'created': created, 'updated': updated, 'replaced': replaced, 'protected': protected, 'errors': errors}


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
            'script_before': r.script_before or '',
            'script_during': r.script_during or '',
            'script_after': r.script_after or '',
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
