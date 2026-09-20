"""Alice keeps the installation's Connection to WC_HQ.

A new installation has no relationship to webclerk.com until something
establishes one. That something is Alice, not a seed script and not a
silent constant buried in code: the Connection is a *record*, visible in
the UI, editable by the owner, and deactivatable at any time. Alice
creates it the first time the installation needs something from HQ, and
writes an alice_log note saying she did.

What this Connection permits is narrow and stated on the record: pull the
public recommended set (Settings, Reports, the GL role map). No business
data moves. Pulling a public bundle is not "speaking to HQ" in the sense
that apps/sync/services/connections.py governs — that rule covers
registering, relaying, escalating and sending reviews, and it is the
*upstream* Connection that carries it.

The owner may deactivate this record. An installation whose owner has
deactivated it simply stops asking, and keeps whatever it already has.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

HQ_CONNECTION_IDA = 'wchq-conn-downstream'
HQ_DEFAULT_URL = 'https://www.webclerk.com'

# Named bundles this installation may pull. Served by HQ at
# /wcapi/get/bundle_<name>.json — see apps/core/services/bundle_catalogue.py.
HQ_BUNDLE_ENDPOINTS = {
    'init': '/wcapi/get/bundle_init.json',
    'gls': '/wcapi/get/bundle_gls.json',
    'reports': '/wcapi/get/bundle_reports.json',
    'settings': '/wcapi/get/bundle_settings.json',
}


def _hq_base_url() -> str:
    """WCHQ_URL from .env when set, else webclerk.com."""
    try:
        from apps.sync.services.connections import wchq_link
        base = wchq_link()[0]
        if base:
            return base.rstrip('/')
    except Exception:
        pass
    return HQ_DEFAULT_URL


def ensure_hq_connection():
    """The Connection record to webclerk.com. Alice creates it if it is absent.

    Returns the Connection, or None when the model is unavailable. An existing
    record is returned untouched — including one the owner has deactivated,
    which the caller must check.
    """
    try:
        from apps.sync.models.connection import Connection
    except Exception as exc:
        logger.debug('[ALICE] Connection model unavailable: %s', exc)
        return None

    existing = Connection.objects.filter(ida=HQ_CONNECTION_IDA).first()
    if existing is not None:
        return existing

    conn = Connection.objects.create(
        ida=HQ_CONNECTION_IDA,
        name='WC_HQ Downstream',
        type='api',
        purpose='sync',
        status='active',
        config={
            'channel': 'api',
            'direction': 'pull',
            'endpoint': _hq_base_url(),
            'endpoints': dict(HQ_BUNDLE_ENDPOINTS),
            'auth_method': 'none',
            'content_types': sorted(HQ_BUNDLE_ENDPOINTS),
        },
        rules={
            'receiving': {
                'public_bundles_no_auth': True,
                'no_business_data_ever': True,
                'baseline_merge_only': True,
            },
        },
        metadata={
            'created_by': 'alice',
            'reason': 'installation needed a recommended set and had no link to WC_HQ',
        },
    )
    logger.info('[ALICE] created the WC_HQ Connection (%s)', conn.pk)
    _note_connection_created(conn)
    return conn


def _note_connection_created(conn) -> None:
    """Alice says what she did. Never fails the caller."""
    try:
        from apps.ai_assistant.services.notes import create_note

        create_note(
            'log',
            role='system',
            name='WC_HQ connection created',
            parent_model='connection',
            details={
                'connection_id': conn.pk,
                'ida': HQ_CONNECTION_IDA,
                'endpoint': (conn.config or {}).get('endpoint'),
                'reason': 'this installation asked for a recommended set and had no link to WC_HQ',
                'permits': 'pull public bundles only — no business data',
                'source': 'alice.ensure_hq_connection',
            },
        )
    except Exception as exc:
        logger.debug('[ALICE] could not note the connection: %s', exc)


def bundle_url(name: str) -> tuple[str, str]:
    """(url, error) for a named bundle, through the Connection Alice keeps.

    An inactive Connection is honoured: the owner turned the link off, so
    there is no URL and that is not an error to escalate.
    """
    if name not in HQ_BUNDLE_ENDPOINTS:
        return '', f'unknown bundle "{name}". Known: {", ".join(sorted(HQ_BUNDLE_ENDPOINTS))}.'

    conn = ensure_hq_connection()
    if conn is None:
        return _hq_base_url() + HQ_BUNDLE_ENDPOINTS[name], ''

    if not (conn.is_active and conn.status == 'active'):
        return '', 'the WC_HQ connection is turned off on this installation'

    config = conn.config if isinstance(conn.config, dict) else {}
    base = (config.get('endpoint') or _hq_base_url()).rstrip('/')
    endpoint = (config.get('endpoints') or {}).get(name) or HQ_BUNDLE_ENDPOINTS[name]
    return base + endpoint, ''
