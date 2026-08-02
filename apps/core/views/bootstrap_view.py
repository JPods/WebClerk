"""
Bootstrap View — serves company prefs to React at startup.

Returns currency, order_defaults, price_levels, and behavior settings
from the company-profile Setting. Versioned with a hash so React only
re-downloads when something changes.

Usage:
  GET /wcapi/bootstrap/              → full payload
  GET /wcapi/bootstrap/?v=<hash>     → 304 if unchanged
"""
import hashlib
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class BootstrapView(APIView):
    http_method_names = ["get", "options", "head"]

    def get(self, request):
        from apps.core.models import Setting

        try:
            setting = Setting.objects.get(ida='company-profile', purpose='company_profile')
        except Setting.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Company profile not configured'},
                status=status.HTTP_404_NOT_FOUND,
            )

        prefs = setting.prefs or {}
        config = setting.config or {}

        # Build the bootstrap payload — only what React needs
        payload = {
            'currency': prefs.get('currency', {}),
            'order_defaults': prefs.get('order_defaults', {}),
            'price_levels': prefs.get('price_levels', {}),
            'inventory': prefs.get('inventory', {}),
            'commissions': prefs.get('commissions', {}),
            'collections': prefs.get('collections', {}),
            'document_text': prefs.get('document_text', {}),
            'behavior': prefs.get('behavior', {}),
            'fiscal': prefs.get('fiscal', {}),
            'company': config.get('company', {}),
            'logos': config.get('logos', {}),
            'print_defaults': config.get('print_defaults', {}),
        }

        # Version hash — changes when prefs or company config change
        version = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        payload['_version'] = version

        # If client sends ?v=<hash> and it matches, return 304
        client_version = request.query_params.get('v')
        if client_version and client_version == version:
            return Response(status=status.HTTP_304_NOT_MODIFIED)

        return Response({'status': 'success', 'data': payload})
