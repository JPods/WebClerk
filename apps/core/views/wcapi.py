from __future__ import annotations
from typing import Any, Dict, List, Optional

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer

from apps.core.services import wcapi as services
from apps.core.utils import policy
from apps.core.utils.registry import resolve

# Import serializers for transaction models to include lines
try:
    from apps.transactions.serializers.transaction_serializers import (
        ProposalSerializer, SalesOrderSerializer, PurchaseOrderSerializer
    )
    TRANSACTION_SERIALIZERS = {
        'proposal': ProposalSerializer,
        'salesorder': SalesOrderSerializer,
        'purchaseorder': PurchaseOrderSerializer,
    }
except ImportError:
    TRANSACTION_SERIALIZERS = {}

try:  # pragma: no cover - optional dependency in some deployments
    from apps.core.utils.model_policies import model_policies as mp  # noqa: F401
except Exception:  # pragma: no cover - fallback if policies unavailable
    mp = None


WcapiResponseSerializer = inline_serializer(
    name="WcapiResponse",
    fields={
        "record": serializers.JSONField(required=False, help_text="Single record when id parameter is provided"),
        "results": serializers.ListField(required=False, child=serializers.JSONField(), help_text="List of records"),
        "count": serializers.IntegerField(required=False, help_text="Number of records returned in this response"),
        "total": serializers.IntegerField(required=False, help_text="Total number of records matching the query"),
        "limit": serializers.IntegerField(required=False, help_text="Requested limit"),
        "offset": serializers.IntegerField(required=False, help_text="Applied offset"),
        "detail": serializers.CharField(required=False, help_text="Error message if request failed"),
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
        limit: int = 500,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        ordering: Optional[str] = None,
    ) -> Response:
        if not resolve(model_key):
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        if record_id is not None:
            obj = services.get_item(model_key, request=request, id=record_id)
            if not obj:
                return Response({"record": None}, status=status.HTTP_200_OK)

            # Use serializer for transaction models to include lines
            if model_key in TRANSACTION_SERIALIZERS:
                serializer_class = TRANSACTION_SERIALIZERS[model_key]
                serializer = serializer_class(obj, context={'request': request})
                return Response({"record": serializer.data}, status=status.HTTP_200_OK)

            allow = policy.field_allowlist(type(obj), request=request)
            return Response({"record": services.to_dict(obj, allow=allow)}, status=status.HTTP_200_OK)

        # Get total count for pagination info
        ModelCls, qs = services.get_queryset(model_key, request=request)
        if filters:
            qs = qs.filter(**filters)
        total_count = qs.count()

        # Apply ordering and pagination
        if ordering:
            qs = qs.order_by(ordering)

        # Apply offset and limit
        qs = qs[offset:offset + limit]
        items = list(qs)

        allow = policy.field_allowlist(type(items[0]), request=request) if items else None
        results = [services.to_dict(o, allow=allow) for o in items]

        return Response({
            "results": results,
            "count": len(results),
            "total": total_count,
            "limit": limit,
            "offset": offset
        }, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="wcapi_get_list_query",
        summary="Get any model records",
        description="Retrieve records from any configured model using query parameters. Supports filtering, pagination, and field selection.",
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Model key from WCAPI registry (e.g., 'contact', 'invoice', 'salesorder')",
            ),
            OpenApiParameter(
                name="id",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Specific record ID to retrieve (returns single item instead of list)",
            ),
            OpenApiParameter(
                name="fields",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Comma-separated list of fields to include in response (e.g., 'id,name,status')",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Maximum number of records to return (default: 500, max: 1000)",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Number of records to skip for pagination (use with limit)",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Field to order by (prefix with '-' for descending, e.g., '-dt_created')",
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
            return Response({"detail": "model_name parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        record_id = request.query_params.get("id")
        fields = request.query_params.get("fields")
        fields_list = [f.strip() for f in fields.split(",")] if isinstance(fields, str) else None

        # Parse limit with bounds checking
        limit = request.query_params.get("limit", "500")
        try:
            limit_int = min(int(limit), 1000)  # Max 1000 records
            if limit_int <= 0:
                limit_int = 500
        except ValueError:
            limit_int = 500

        # Parse offset
        offset = request.query_params.get("offset", "0")
        try:
            offset_int = max(int(offset), 0)  # Ensure non-negative
        except ValueError:
            offset_int = 0

        order_by = request.query_params.get("order_by")
        # Map created_at to dt_created for ordering
        if order_by == "created_at":
            order_by = "dt_created"
        elif order_by == "-created_at":
            order_by = "-dt_created"

        # Parse additional filters from query params
        filters = {}
        for key, value in request.query_params.items():
            if key not in ['model_name', 'id', 'fields', 'limit', 'offset', 'order_by']:
                filters[key] = value

        # Handle special filter key for model_name
        model_name_filter = request.query_params.get('model_name_filter')
        if model_name_filter:
            filters['model_name'] = model_name_filter

        return self._handle(model_key, record_id, fields_list, request, limit_int, offset_int, filters, order_by)


class ModelNameListView(APIView):
    """List available model names."""

    http_method_names = ["get", "options", "head"]

    @extend_schema(
        operation_id="model_name_list",
        summary="Get list of model names",
        description="Retrieve list of available model names for the admin workbench.",
        responses={
            200: inline_serializer(
                name="ModelNameListResponse",
                fields={
                    "model_names": serializers.ListField(child=serializers.CharField()),
                    "count": serializers.IntegerField(),
                },
            ),
        },
    )
    def get(self, request, **kwargs):
        from django.apps import apps
        from apps.core.utils.registry import resolve
        models = apps.get_models()
        model_names = [model._meta.model_name for model in models if model._meta.model_name != "setting" and resolve(model._meta.model_name)]
        return Response({
            "status": "success",
            "code": 200,
            "message": "OK",
            "data": {"model_names": model_names, "count": len(model_names)}
        }, status=status.HTTP_200_OK)


class ModelDetailView(APIView):
    """Get model details including fields."""

    http_method_names = ["get", "options", "head"]

    @extend_schema(
        operation_id="model_detail",
        summary="Get model details",
        description="Retrieve model metadata including field definitions.",
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Model key to get details for",
            ),
        ],
        responses={
            200: inline_serializer(
                name="ModelDetailResponse",
                fields={
                    "model": inline_serializer(
                        name="ModelInfo",
                        fields={
                            "model_name": serializers.CharField(),
                            "fields": serializers.ListField(child=serializers.JSONField()),
                        },
                    ),
                },
            ),
            400: inline_serializer(
                name="ErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, **kwargs):
        from apps.core.utils.registry import resolve
        model_key = request.query_params.get("model_name")
        if not model_key:
            return Response({"detail": "model_name required"}, status=status.HTTP_400_BAD_REQUEST)

        ModelCls = resolve(model_key)
        if not ModelCls:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        fields = []
        for f in ModelCls._meta.fields:
            fields.append({"name": f.name, "type": f.__class__.__name__})

        return Response(
            {
                "status": "success",
                "code": 200,
                "message": "OK",
                "data": {
                    "model": {
                        "model_name": model_key,
                        "fields": fields,
                    }
                }
            },
            status=status.HTTP_200_OK,
        )
