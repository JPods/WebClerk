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
        company = body.get('company', {})
        onboarding = body.get('onboarding', {})

        # Generate a unique token for this installation
        raw = f"{installation_id}:{secrets.token_hex(32)}:{dt_registered}"
        token = hashlib.sha256(raw.encode()).hexdigest()

        # Store registration as a Contact + Document record
        # Contact = the installation's primary contact
        # Document = the onboarding profile (what they need, their challenges)
        try:
            from apps.docs.models.document import Document
            Document.objects.create(
                ida=f'wchq-reg-{installation_id[:8]}',
                name=f"Installation: {company.get('name') or installation_id[:12]}",
                purpose='wchq-registration',
                status='active',
                config={
                    'installation_id': installation_id,
                    'token_prefix': token[:12],
                    'dt_registered': dt_registered,
                    'company': company,
                    'onboarding': onboarding,
                },
                metadata={
                    'industry': onboarding.get('industry', ''),
                    'business_type': onboarding.get('business_type', ''),
                    'locale': onboarding.get('locale', 'en-US'),
                    'data_import_challenges': onboarding.get('data_import_challenges', []),
                    'what_would_help': onboarding.get('what_would_help', []),
                },
            )
        except Exception as e:
            logger.warning("[WCHQ] Failed to store registration document: %s", e)

        logger.info(
            "[WCHQ] Installation registered: %s industry=%s token=%s...",
            installation_id,
            onboarding.get('industry', '?'),
            token[:12],
        )

        return JsonResponse({
            'token': token,
            'installation_id': installation_id,
            'dt_registered': dt_registered,
            'status': 'registered',
        }, status=201)
