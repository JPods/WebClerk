from __future__ import annotations
from typing import Any, List, Optional

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer

from apps.core.services import wcapi as services
from apps.core.utils import policy
from apps.core.utils.registry import resolve

try:  # pragma: no cover - optional dependency in some deployments
    from apps.core.utils.model_policies import model_policies as mp  # noqa: F401
except Exception:  # pragma: no cover - fallback if policies unavailable
    mp = None


WcapiResponseSerializer = inline_serializer(
    name="WcapiResponse",
    fields={
        "item": serializers.JSONField(required=False),
        "items": serializers.ListField(required=False, child=serializers.JSONField()),
        "detail": serializers.CharField(required=False),
    },
)


class WCAPIGetView(APIView):
    """Read-only WCAPI endpoint supporting query-parameter access."""

    http_method_names = ["get", "options", "head"]

    def _handle(
        self,
        model_key: str,
        record_id: Optional[Any],
        fields: Optional[List[str]],
        request,
    ) -> Response:
        if not resolve(model_key):
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        if record_id is not None:
            obj = services.get_item(model_key, request=request, id=record_id)
            if not obj:
                return Response({"item": None}, status=status.HTTP_200_OK)
            allow = policy.field_allowlist(type(obj), request=request)
            return Response({"item": services.to_dict(obj, allow=allow)}, status=status.HTTP_200_OK)

        items = services.list_items(model_key, request=request, filters={})
        allow = policy.field_allowlist(type(items[0]), request=request) if items else None
        return Response({"items": [services.to_dict(o, allow=allow) for o in items]}, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="wcapi_get_list_query",
        summary="Get any model records",
        description="Retrieve records from any configured model using query parameters.",
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Model key from WCAPI registry (e.g., 'contact', 'action')",
            ),
            OpenApiParameter(
                name="id",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Specific record ID to retrieve (returns single item)",
            ),
            OpenApiParameter(
                name="fields",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Comma-separated list of fields to include in response",
            ),
        ],
        responses={
            200: WcapiResponseSerializer,
            400: WcapiResponseSerializer,
            401: WcapiResponseSerializer,
        },
    )
    def get(self, request, **kwargs):
        model_key = request.query_params.get("model_name")
        if not model_key:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        record_id = request.query_params.get("id")
        fields = request.query_params.get("fields")
        fields_list = [f.strip() for f in fields.split(",")] if isinstance(fields, str) else None
        return self._handle(model_key, record_id, fields_list, request)
