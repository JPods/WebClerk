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


logger = logging.getLogger(__name__)


class WchqSubmitView(APIView):
    """POST {"model_name": "action", "record": {...}} → HQ /wcapi/instance/submit/."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.sync.services.connections import WchqMute, wchq_speak
        try:
            base_url, token = wchq_speak()
        except WchqMute as e:
            return Response({'error': str(e)}, status=503)

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
