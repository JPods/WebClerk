"""Settings bootstrap — fetch or import Settings when health check fails.

Two sources:
    1. Git bundle — user pulls settings-bundle.json from repo, uploads it
    2. WC_HQ API — fetch from webclerk.com/wcapi/settings-bundle/

WC_HQ API requires an Athena token. The URL is always webclerk.com/... —
webclerk.com IS the path, not a parameter. No token, no fetch.

Usage:
    from apps.core.services.settings_bootstrap import (
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


def import_settings_bundle(bundle_data: dict | list, force_foundational: bool = False) -> dict[str, Any]:
    """Import a settings bundle — create or update Setting records.

    bundle_data: list of Setting dicts, each with at least:
        uuid, ida, purpose, parent_model, config, metadata, prefs, refs,
        explanation, paths, scope, name

    UUID controls merge: if a Setting with matching UUID exists, update it.
    If not, create it.

    Foundational protection: records with metadata.foundational=true in the
    database are NEVER modified by external bundles. Only unpack_init_bundle
    (which passes force_foundational=True) can update them.

    Returns: {created: int, updated: int, protected: int, errors: [str]}
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

                # Update — baseline merge: add missing keys, never replace existing.
                # WC_HQ settings are the baseline. User customizations win.

                # Scalar fields — only update if currently empty
                for field in ('name', 'scope', 'purpose', 'parent_model'):
                    if field in rec and not getattr(existing, field, None):
                        setattr(existing, field, rec[field])

                # explanation/paths — update if empty (user hasn't written their own)
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
                existing.save()
                updated += 1
            else:
                # Create
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
                s.save()
                created += 1

        except Exception as e:
            errors.append(f"Error on ida={rec.get('ida', '?')}: {e}")
            logger.exception('settings_bootstrap: import error')

    if protected:
        logger.info('settings_bootstrap: %d foundational records protected from external bundle', protected)
    logger.info('settings_bootstrap: created=%d updated=%d protected=%d errors=%d',
                created, updated, protected, len(errors))
    return {'created': created, 'updated': updated, 'protected': protected, 'errors': errors}


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
