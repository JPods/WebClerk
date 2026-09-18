"""Relay a record to WC HQ's instance-submit endpoint.

The browser posts here; the server adds the Athena token and forwards. The token
never reaches the browser. HQ accepts only the models in its ALLOWED_MODELS.
"""
from __future__ import annotations

import logging

import httpx
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_assistant.services.hook_review import wchq_connection
from apps.sync.services.athena_auth import athena_token

logger = logging.getLogger(__name__)


class WchqSubmitView(APIView):
    """POST {"model_name": "action", "record": {...}} → HQ /wcapi/instance/submit/."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        connection = wchq_connection()
        base_url = ((connection.config or {}).get('wchq_base_url') or '') if connection else ''
        token = athena_token(connection) if connection else ''
        if not base_url or not token:
            return Response({'error': 'WC HQ connection has no base url or Athena token'}, status=503)

        body = {'model_name': request.data.get('model_name'), 'record': request.data.get('record')}
        try:
            resp = httpx.post(
                base_url.rstrip('/') + '/wcapi/instance/submit/',
                json=body,
                headers={'Authorization': f'Athena {token}'},
                timeout=15,
            )
        except httpx.HTTPError as e:
            logger.warning('[WCHQ] submit relay failed: %s', e)
            return Response({'error': f'WC HQ unreachable: {type(e).__name__}'}, status=502)
        try:
            payload = resp.json()
        except ValueError:
            payload = {'error': resp.text[:500]}
        return Response(payload, status=resp.status_code)
