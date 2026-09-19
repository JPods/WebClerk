"""Connections — where every key and outside endpoint lives (Bill, 2026-09-18).

Settings are read by every login, so no credential goes in one. A service this
server talks to — a carrier, a gateway, an API, SMTP, the Allie agent bus — is a
Connection record: config.channel names it, config.endpoint says where, and
encryption.credentials holds the keys. `encryption` never leaves the server
(field_leaves.NEVER_EXPOSED); `config` is shown in the UI and returned by the API.

.env keeps only what is needed before the database can be trusted
(common/instance_env.py): the database password, SECRET_KEY, the WC_HQ support
link, the Alice and Andi logins, and OLLAMA_BASE_URL.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConnectionUnavailable(Exception):
    """No single active Connection for a channel on this server."""


def active_connection(channel: str):
    """The one active Connection whose config.channel is `channel`. Raises
    ConnectionUnavailable when there is none or more than one — never guesses."""
    from apps.sync.models import Connection
    rows = list(Connection.objects.filter(status='active', is_active=True,
                                          config__channel=channel)[:2])
    if len(rows) != 1:
        raise ConnectionUnavailable(
            f"expected one active Connection with channel {channel!r} on this server, found {len(rows)}")
    return rows[0]


def credentials(connection) -> dict:
    """encryption.credentials, validated (ConnectionCredentials)."""
    from apps.sync.models.connection_pydantic import ConnectionCredentials
    enc = connection.encryption if isinstance(connection.encryption, dict) else {}
    return ConnectionCredentials.model_validate(enc.get('credentials') or {}).model_dump()


def set_credentials(connection, values: dict) -> None:
    """Replace encryption.credentials (validated). The caller saves."""
    from apps.sync.models.connection_pydantic import ConnectionCredentials
    enc = connection.encryption if isinstance(connection.encryption, dict) else {}
    enc['credentials'] = ConnectionCredentials.model_validate(values).model_dump()
    connection.encryption = enc


def wchq_link() -> tuple[str, str]:
    """(url, api_key) for WC_HQ — from .env, so support works when the database is damaged."""
    from django.conf import settings
    return (settings.WCHQ_URL or '').rstrip('/'), settings.WCHQ_API_KEY or ''


def connect_agent_bus():
    """psycopg2 connection to the Allie agent bus (channel 'agent_bus').

    config.endpoint is a libpq URI without the password, e.g.
    postgresql://williamjames@localhost/allie; a password, when one is needed,
    is encryption.credentials.password.
    """
    import psycopg2
    conn = active_connection('agent_bus')
    endpoint = (conn.config or {}).get('endpoint') or ''
    if not endpoint:
        raise ConnectionUnavailable(f"Connection {conn.pk} ({conn.name}) has no config.endpoint")
    password = credentials(conn).get('password') or None
    return psycopg2.connect(endpoint, password=password) if password else psycopg2.connect(endpoint)


# ── Speaking to WC_HQ ───────────────────────────────────────────────────
# An instance is mute toward WC_HQ by default (Bill, 2026-09-18). It speaks only
#   1. to report an attack (reason='attack'), or
#   2. when an active Connection documents the relationship: ida 'wchq-conn-upstream',
#      status 'active' — the owner's decision, recorded where anyone can see it.
# Pulling public bundles is not speaking; registering, relaying, escalating and
# sending reviews are.
WCHQ_RELATIONSHIP_IDA = 'wchq-conn-upstream'


class WchqMute(Exception):
    """This instance does not speak to WC_HQ right now."""


def wchq_relationship():
    """The active Connection documenting this instance's relationship with WC_HQ, or None."""
    from apps.sync.models import Connection
    return Connection.objects.filter(ida=WCHQ_RELATIONSHIP_IDA, status='active', is_active=True).first()


def wchq_speak(reason: str = '') -> tuple[str, str]:
    """(url, api_key) when this instance may speak to WC_HQ; raises WchqMute otherwise."""
    url, key = wchq_link()
    if reason != 'attack' and wchq_relationship() is None:
        raise WchqMute(f"mute: no active '{WCHQ_RELATIONSHIP_IDA}' Connection documents a relationship with WC_HQ")
    if not url or not key:
        raise WchqMute('mute: WCHQ_URL / WCHQ_API_KEY not set in .env')
    return url, key
