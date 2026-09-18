"""Burndown API endpoint — returns sprint burndown data."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.services.action_burndown import calculate_burndown


class BurndownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        data = calculate_burndown(project_id)
        return Response({"status": "success", "data": data})
