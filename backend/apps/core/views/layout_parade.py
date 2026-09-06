"""
Layout Parade — API endpoint for the layout audit tool.

Returns layout coverage for all registered models so the frontend
can display gaps and coverage in a browsable view.

Endpoint:
  GET /wcapi/_layout_parade/  — full audit with summary
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.management.commands.audit_layouts import audit_all_layouts, audit_summary

logger = logging.getLogger(__name__)


class LayoutParadeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return layout coverage audit for all models."""
        gaps_only = request.query_params.get('gaps_only', '').lower() in ('1', 'true', 'yes')

        results = audit_all_layouts()
        summary = audit_summary(results)

        if gaps_only:
            results = [r for r in results if r['needs_attention']]

        return Response({
            'summary': summary,
            'models': results,
        })
