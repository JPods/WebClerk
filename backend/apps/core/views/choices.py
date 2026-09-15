from __future__ import annotations

from typing import List

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.choices_registry import (
    build_choices_payload,
    collect_default_select_lists,
    get_registry_errors,
)


class ChoiceCatalogView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List default select lists captured in choices modules",
        parameters=[
            OpenApiParameter(
                name="app",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter to one or more Django app labels (repeatable)",
                many=True,
            ),
            OpenApiParameter(
                name="refresh",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="When true, rebuild the choice cache before responding",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Aggregated choice lists grouped by app/model/field"),
        },
    )
    def get(self, request):
        apps_requested: List[str] = request.query_params.getlist("app")
        refresh_flag = request.query_params.get("refresh", "").lower()
        if refresh_flag in {"1", "true", "yes"}:
            collect_default_select_lists.cache_clear()
        app_filter = apps_requested or None
        choices = build_choices_payload(app_filter)
        meta = {
            "app_count": len(choices),
            "model_count": sum(len(models) for models in choices.values()),
            "errors": get_registry_errors(),
        }
        return Response({"apps": choices, "meta": meta})
