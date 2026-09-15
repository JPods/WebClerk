from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404

from apps.sync.models.connection import Connection
from apps.sync.services.google_calendar import (
    get_authorization_url,
    exchange_code_for_tokens,
    list_events,
)


class GCAL_StartAuthView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    ALLOWED_ROLES = {'staff', 'admin'}

    def get(self, request):
        user = request.user
        if not (getattr(user, 'role', '') in self.ALLOWED_ROLES or user.is_superuser):
            return Response({'detail': 'Forbidden'}, status=403)
        conn_id = int(request.GET.get('connection_id') or 0)
        conn = get_object_or_404(Connection, pk=conn_id)
        if conn.type != 'google_calendar':
            return Response({'detail': 'Connection.type must be google_calendar'}, status=400)
        try:
            url = get_authorization_url(conn)
            return Response({'authorization_url': url})
        except Exception as e:
            return Response({'detail': str(e)}, status=400)


class GCAL_OAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]  # Google redirects here without cookies

    def get(self, request):
        conn_id = int(request.GET.get('connection_id') or 0)
        code = request.GET.get('code')
        state = request.GET.get('state')
        if not conn_id or not code:
            return Response({'detail': 'Missing connection_id or code'}, status=400)
        conn = get_object_or_404(Connection, pk=conn_id)

        # Validate OAuth state to prevent request confusion attacks.
        # The state was set during authorization and stored on the Connection.
        expected_state = (conn.config or {}).get('oauth_state', '')
        if not expected_state or state != expected_state:
            return Response({'detail': 'Invalid or missing OAuth state'}, status=403)
        try:
            token_info = exchange_code_for_tokens(conn, code)
            # Mask sensitive fields in the response; do not include id_token or secrets
            redacted = {}
            for k, v in token_info.items():
                if k in ('token', 'refresh_token', 'client_secret', 'id_token'):
                    redacted[k] = '...'
                else:
                    redacted[k] = v
            return Response({'status': 'ok', 'tokens': redacted, 'connection_id': conn.id})
        except Exception as e:
            return Response({'detail': str(e)}, status=400)


class GCAL_ListEventsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    ALLOWED_ROLES = {'staff', 'admin'}

    def get(self, request):
        user = request.user
        if not (getattr(user, 'role', '') in self.ALLOWED_ROLES or user.is_superuser):
            return Response({'detail': 'Forbidden'}, status=403)
        conn_id = int(request.GET.get('connection_id') or 0)
        cal_id = request.GET.get('calendar_id') or 'primary'
        max_results = int(request.GET.get('max_results') or 10)
        conn = get_object_or_404(Connection, pk=conn_id)
        if conn.type != 'google_calendar':
            return Response({'detail': 'Connection.type must be google_calendar'}, status=400)
        try:
            data = list_events(conn, calendar_id=cal_id, max_results=max_results)
            return Response(data)
        except Exception as e:
            return Response({'detail': str(e)}, status=400)
