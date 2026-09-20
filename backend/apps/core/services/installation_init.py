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
from typing import Any

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


# These bundles are authored once at WC_HQ and distributed, so every installation
# derives or receives the same uuid for the same record — uuid is the identity.
# (For data two systems created independently, a natural key is required instead;
# apps/core/services/record_import.py carries the scar that says why.)
BUNDLE_PARTS = (
    # bundle key      model label           the recommended set is the authority
    ('settings',      'core.Setting'),
    ('gl_accounts',   'accounts.GlAccount'),
    ('reports',       'core.Report'),
)


def load_bundle(bundle: dict, *, dry_run: bool = False) -> dict[str, Any]:
    """Load a recommended set. Baseline merge — the owner's values stand.

    The chart goes in before the reports and the role map that point into it,
    which is why BUNDLE_PARTS is ordered.
    """
    from apps.core.services.record_import import import_records

    result: dict[str, Any] = {'errors': []}
    for key, model_label in BUNDLE_PARTS:
        records = bundle.get(key) or []
        part = import_records(
            model_label, records,
            match_on=('uuid',),
            authoritative=True,      # the recommended set owns foundational records
            dry_run=dry_run,
        )
        result[key] = {'created': part['created'], 'updated': part['updated']}
        result['errors'].extend(part['errors'])
    return result


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
