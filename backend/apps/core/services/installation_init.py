"""Installation init — how an installation gets what it has not been given.

An installation that has no report definitions, no chart of accounts, or no
GL role map is not broken and must not be told that it is. It asks
www.webclerk.com for the bundle that carries what it is missing, loads it,
and carries on. Only when the recommendation itself cannot be obtained — HQ
unreachable *and* no shipped copy on disk — is there anything to report.

Three sources, in order of authority:

    1. WC_HQ            the *current* recommendation — /wcapi/get/bundle_<name>.json
    2. init-bundle.json the *shipped* recommendation — this release's copy on disk
    3. the installation what the owner has since decided — never overwritten

Loading is a baseline merge on uuid: missing records and missing keys are
added, existing values are left exactly as the owner set them. Asking HQ can
fill a default the owner never had. It can never change one they chose.

The link to HQ is a Connection record that Alice creates
(apps/core/services/alice_connections.py) — visible, editable, and switchable
off by the owner. Which bundle carries which definition set is declared once,
in apps/core/services/bundle_catalogue.py.

This module is the only place that fetches or loads a bundle. ``db_init``,
``unpack_init_bundle`` and the runtime self-heal all come through here.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# This release's shipped copy — backend/init-bundle.json.
GIT_BUNDLE_PATH = Path(__file__).resolve().parents[3] / 'init-bundle.json'

FETCH_TIMEOUT = 30


# ---------------------------------------------------------------- fetching


def unwrap_envelope(payload: Any) -> dict | None:
    """A bundle, whether or not it arrived inside the API envelope.

    Every WC3 JSON endpoint answers ``{status, error, code, message, data}``,
    so a bundle served by HQ is nested under ``data``. A bundle read from disk
    is not. Accept both and return the bundle itself.
    """
    if not isinstance(payload, dict):
        return None
    if _carries_records(payload):
        return payload
    inner = payload.get('data')
    if isinstance(inner, dict) and _carries_records(inner):
        return inner
    return None


def _carries_records(payload: dict) -> bool:
    return any(k in payload for k in ('settings', 'reports', 'gl_accounts'))


def fetch_from_hq(name: str = 'init', *, url: str | None = None,
                  timeout: int = FETCH_TIMEOUT) -> tuple[dict | None, str]:
    """A named bundle from WC_HQ, through the Connection. Returns (bundle, error).

    ``url`` overrides the Connection — for an operator pointing db_init at a
    specific host.
    """
    from apps.core.services.alice_connections import bundle_url

    if url is None:
        url, err = bundle_url(name)
        if err:
            return None, err

    try:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'WebClerk3-init-bundle/1.0',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, f'WC_HQ returned HTTP {resp.status} for {url}'
            payload = json.loads(resp.read().decode('utf-8'))
    except urllib.error.URLError as exc:
        return None, f'WC_HQ unreachable: {exc.reason}'
    except json.JSONDecodeError as exc:
        return None, f'WC_HQ returned invalid JSON: {exc}'
    except Exception as exc:
        return None, f'WC_HQ fetch failed: {exc}'

    bundle = unwrap_envelope(payload)
    if bundle is None:
        return None, f'WC_HQ response for "{name}" carried no records'
    return bundle, ''


def load_from_disk(path: str | Path | None = None) -> tuple[dict | None, str]:
    """This release's shipped recommended set. Returns (bundle, error)."""
    bundle_path = Path(path) if path else GIT_BUNDLE_PATH
    if not bundle_path.exists():
        return None, f'no shipped bundle at {bundle_path}'
    try:
        with open(bundle_path) as fh:
            payload = json.load(fh)
    except Exception as exc:
        return None, f'could not read {bundle_path}: {exc}'
    bundle = unwrap_envelope(payload)
    if bundle is None:
        return None, f'{bundle_path} carried no records'
    return bundle, ''


def get_bundle(name: str = 'init', *, offline: bool = False,
               path: str | Path | None = None) -> tuple[dict | None, str, str]:
    """A recommended set: HQ first, the shipped copy second.

    Returns (bundle, source, error). ``source`` is 'wchq' or 'disk'.
    An error is returned only when neither source could supply one.
    """
    if not offline:
        bundle, err = fetch_from_hq(name)
        if bundle is not None:
            return bundle, 'wchq', ''
        logger.info('[INIT_BUNDLE] %s — falling back to the shipped copy', err)

    bundle, disk_err = load_from_disk(path)
    if bundle is not None:
        return bundle, 'disk', ''
    return None, '', disk_err


# ----------------------------------------------------------------- loading


def deep_merge_baseline(existing: dict, incoming: dict) -> dict:
    """Add the keys the owner does not have. Never replace one they do."""
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_baseline(merged[key], value)
    return merged


def _model(app_label: str, model_name: str):
    from django.apps import apps as dj_apps

    try:
        return dj_apps.get_model(app_label, model_name)
    except LookupError:
        return None


REPORT_SCALARS = (
    'name', 'description', 'model_name', 'purpose', 'record_id', 'output_type',
    'category', 'role_required', 'sort_order', 'explanation',
)
REPORT_JSON = ('config', 'metadata', 'refs', 'paths')


def load_reports(records: Iterable[dict], *, dry_run: bool = False) -> dict[str, Any]:
    """Merge Report records from a bundle. uuid controls the merge."""
    Report = _model('core', 'Report')
    if Report is None:
        return {'created': 0, 'updated': 0, 'errors': ['Report model not found']}

    created = updated = 0
    errors: list[str] = []

    for rec in records:
        uuid_val = rec.get('uuid')
        if not uuid_val:
            errors.append(f"Report missing uuid: name={rec.get('name', '?')}")
            continue
        existing = Report.objects.filter(uuid=uuid_val).first()
        if dry_run:
            updated += 1 if existing else 0
            created += 0 if existing else 1
            continue

        if existing:
            for field in REPORT_SCALARS:
                if field in rec:
                    setattr(existing, field, rec[field])
            for field in REPORT_JSON:
                if field not in rec:
                    continue
                current = getattr(existing, field, None) or {}
                incoming = rec[field] or {}
                if isinstance(current, dict) and isinstance(incoming, dict):
                    setattr(existing, field, deep_merge_baseline(current, incoming))
                elif not current:
                    setattr(existing, field, incoming)
            meta = existing.metadata or {}
            meta['foundational'] = True
            existing.metadata = meta
            existing.save()
            updated += 1
        else:
            kwargs: dict[str, Any] = {'uuid': uuid_val, 'ida': rec.get('ida', '')}
            for field in REPORT_SCALARS:
                if field in rec:
                    kwargs[field] = rec[field]
            for field in REPORT_JSON:
                kwargs[field] = rec.get(field, {})
            meta = kwargs.get('metadata') or {}
            meta['foundational'] = True
            kwargs['metadata'] = meta
            kwargs['prefs'] = rec.get('prefs', {})
            for field in ('editor_type', 'content'):
                if field in rec:
                    kwargs[field] = rec[field]
            Report.objects.create(**kwargs)
            created += 1

    return {'created': created, 'updated': updated, 'errors': errors}


def load_gl_accounts(records: Iterable[dict], *, dry_run: bool = False) -> dict[str, Any]:
    """Merge chart-of-accounts records. An account the owner already has is left alone."""
    from apps.core.services.bundle_catalogue import GL_ACCOUNT_FIELDS

    GlAccount = _model('accounts', 'GlAccount')
    if GlAccount is None:
        return {'created': 0, 'updated': 0, 'errors': []}

    created = updated = 0
    errors: list[str] = []

    for rec in records:
        ida = (rec.get('ida') or '').strip()
        if not ida:
            errors.append(f"GL account missing ida: name={rec.get('name', '?')}")
            continue
        # ida is the sole account identifier (apps/accounts/services/chart.py).
        if GlAccount.objects.filter(ida=ida).exists():
            updated += 1
            continue
        if dry_run:
            created += 1
            continue
        kwargs: dict[str, Any] = {'ida': ida}
        if rec.get('uuid'):
            kwargs['uuid'] = rec['uuid']
        for field in GL_ACCOUNT_FIELDS:
            if field in rec and rec[field] is not None:
                kwargs[field] = rec[field]
        kwargs['config'] = rec.get('config') or {}
        kwargs['metadata'] = {**(rec.get('metadata') or {}), 'foundational': True}
        try:
            GlAccount.objects.create(**kwargs)
            created += 1
        except Exception as exc:
            errors.append(f'GL account {ida}: {exc}')

    return {'created': created, 'updated': updated, 'errors': errors}


def load_bundle(bundle: dict, *, dry_run: bool = False) -> dict[str, Any]:
    """Load a recommended set. Baseline merge — the owner's values stand."""
    from apps.core.services.setting_bootstrap import import_settings_bundle

    settings_recs = bundle.get('settings') or []
    reports_recs = bundle.get('reports') or []
    gl_recs = bundle.get('gl_accounts') or []

    if dry_run:
        from apps.core.models.setting import Setting
        keyed = [r for r in settings_recs if r.get('uuid')]
        s_created = sum(1 for r in keyed if not Setting.objects.filter(uuid=r['uuid']).exists())
        s_result = {'created': s_created, 'updated': len(keyed) - s_created, 'errors': []}
    else:
        # The recommended set is the authority on foundational records.
        s_result = import_settings_bundle(settings_recs, force_foundational=True)

    # The chart goes in before the reports and the role map that point into it.
    g_result = load_gl_accounts(gl_recs, dry_run=dry_run)
    r_result = load_reports(reports_recs, dry_run=dry_run)

    return {
        'settings': {'created': s_result.get('created', 0),
                     'updated': s_result.get('updated', 0)},
        'reports': {'created': r_result['created'], 'updated': r_result['updated']},
        'gl_accounts': {'created': g_result['created'], 'updated': g_result['updated']},
        'errors': (list(s_result.get('errors') or [])
                   + g_result['errors'] + r_result['errors']),
    }


# ------------------------------------------------------------- self-healing

# One installation asks HQ once per definition set per process. A missing
# definition is asked about; it is not polled.
_asked: set[str] = set()


def reset_asked(kind: str | None = None) -> None:
    """Forget that we already asked — for tests and for an explicit re-check."""
    if kind is None:
        _asked.clear()
    else:
        _asked.discard(kind)


def is_defined(kind: str) -> bool:
    from apps.core.services.bundle_catalogue import DEFINITION_BUNDLES

    entry = DEFINITION_BUNDLES.get(kind)
    if entry is None:
        raise ValueError(
            f'Unknown definition set "{kind}". '
            f'Known: {", ".join(sorted(DEFINITION_BUNDLES))}.')
    try:
        return entry[1]()
    except Exception as exc:  # a check that cannot run is not a definition
        logger.debug('[INIT_BUNDLE] check for %s failed: %s', kind, exc)
        return False


def ensure_defined(kind: str, *, force: bool = False) -> bool:
    """Make sure this installation has ``kind`` defined.

    If it does, nothing happens. If it does not, ask WC_HQ for the bundle that
    carries it — falling back to this release's shipped copy — load it, and
    check again. Returns whether ``kind`` is defined when this returns.

    This never raises. A caller that truly cannot proceed without the
    definition says so itself, naming the specific thing it needed.
    """
    from apps.core.services.bundle_catalogue import DEFINITION_BUNDLES

    if is_defined(kind):
        return True
    if kind in _asked and not force:
        return False
    _asked.add(kind)

    bundle_name = DEFINITION_BUNDLES[kind][0]
    bundle, source, err = get_bundle(bundle_name)
    if bundle is None:
        logger.warning(
            '[INIT_BUNDLE] %s is not defined and the "%s" bundle could not be '
            'obtained: %s', kind, bundle_name, err)
        return False

    result = load_bundle(bundle)
    logger.info(
        '[INIT_BUNDLE] %s was not defined — loaded bundle "%s" from %s '
        '(settings +%s, gl_accounts +%s, reports +%s)',
        kind, bundle_name, source,
        result['settings']['created'], result['gl_accounts']['created'],
        result['reports']['created'])
    _record_bundle(kind, bundle_name, source, result)

    return is_defined(kind)


def _record_bundle(kind: str, bundle_name: str, source: str, result: dict) -> None:
    """Leave an audit row for the pull. Never fails the load."""
    try:
        from apps.core.services.alice_connections import ensure_hq_connection
        from apps.sync.models.bundle import Bundle

        conn = ensure_hq_connection()
        if conn is None:
            return
        Bundle.objects.create(
            connection=conn,
            direction='incoming',
            model_name=f'bundle_{bundle_name}',
            status='complete',
            response={'requested_for': kind, 'source': source, **result},
        )
    except Exception as exc:
        logger.debug('[INIT_BUNDLE] could not record the pull: %s', exc)
