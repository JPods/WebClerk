"""Register a new WC3 installation with WCHQ.

POST /wcapi/register-installation/
Called by db_init during database initialization.

Receives an installation_id (UUID), generates a unique Athena token,
stores the registration, and returns the token.

No authentication required for registration — the token IS the
authentication for all subsequent WCHQ communication.
"""
import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class RegisterInstallationView(View):
    """Register a new installation and issue an Athena token."""

    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        installation_id = body.get('installation_id', '')
        if not installation_id:
            return JsonResponse({'error': 'installation_id required'}, status=400)

        dt_registered = body.get('dt_registered', datetime.now(timezone.utc).isoformat())

        # Generate a unique token for this installation
        raw = f"{installation_id}:{secrets.token_hex(32)}:{dt_registered}"
        token = hashlib.sha256(raw.encode()).hexdigest()

        # Log the registration (in production, store in a Registration model)
        logger.info(
            "[WCHQ] Installation registered: %s token=%s...",
            installation_id, token[:12],
        )

        return JsonResponse({
            'token': token,
            'installation_id': installation_id,
            'dt_registered': dt_registered,
            'status': 'registered',
        }, status=201)
