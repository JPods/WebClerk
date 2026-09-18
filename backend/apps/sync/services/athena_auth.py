"""Athena token — the shared secret between an instance and WC HQ.

Lives in Connection.encryption.athena_token (never config: config is shown in the UI
and returned by the API). Only the server reads it; it is never sent to a browser.
"""
from __future__ import annotations

import hmac

from django.http import JsonResponse


def athena_token(connection) -> str:
    encryption = connection.encryption if isinstance(connection.encryption, dict) else {}
    return encryption.get('athena_token') or ''


def set_athena_token(connection, token: str) -> None:
    encryption = connection.encryption if isinstance(connection.encryption, dict) else {}
    encryption['athena_token'] = token
    connection.encryption = encryption


def validate_athena(request):
    """(connection, None) for a request carrying `Authorization: Athena <token>` that
    matches an active Connection; (None, JsonResponse) otherwise."""
    from apps.sync.models.connection import Connection

    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header.startswith('Athena '):
        return None, JsonResponse({'error': 'Missing Authorization: Athena <token>'}, status=401)
    token = header[7:].strip()
    if not token:
        return None, JsonResponse({'error': 'Empty Athena token'}, status=401)

    for connection in Connection.objects.filter(status='active', is_active=True):
        stored = athena_token(connection)
        if stored and hmac.compare_digest(stored, token):
            return connection, None
    return None, JsonResponse({'error': 'Athena token not recognized'}, status=403)
