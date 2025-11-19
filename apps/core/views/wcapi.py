from __future__ import annotations
from typing import Any, Dict, List, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from apps.core.services import wcapi as services
from apps.core.utils import policy
from apps.core.utils.registry import resolve

try:
    from apps.core.utils.model_policies import model_policies as mp
except Exception:
    mp = None

# Request/Response schemas for WCAPI GET
WcapiRequestSerializer = inline_serializer(
    name='WcapiRequest',
    fields={
        'model': serializers.CharField(required=True, help_text='Model key from WCAPI registry (e.g., "contact", "action")'),
        'id': serializers.IntegerField(required=False, help_text='Specific record ID to retrieve (returns single item)'),
        'fields': serializers.CharField(required=False, help_text='Comma-separated list of fields to include in response'),
        'filters': serializers.JSONField(required=False, help_text='JSON object with field filters'),
    }
)

WcapiResponseSerializer = inline_serializer(
    name='WcapiResponse',
    fields={
        'item': serializers.JSONField(required=False),
        'items': serializers.ListField(required=False, child=serializers.JSONField()),
        'detail': serializers.CharField(required=False),
    }
)


class WCAPIGetView(APIView):
    """
    Universal GET endpoint for retrieving data from any configured model.
    
    Supports both GET (query params) and POST (request body) methods with:
    - Single record retrieval by ID
    - List records with filtering and pagination
    - Field selection and projection
    - Model-agnostic data access through WCAPI registry
    """
    http_method_names = ["get", "post", "options", "head"]

    def _handle(self, model_key: str, record_id: Optional[Any], filters: Dict[str, Any], fields: Optional[List[str]], request):
        if not resolve(model_key):
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        if record_id is not None:
            obj = services.get_item(model_key, request=request, id=record_id)
            if not obj:
                return Response({"item": None}, status=status.HTTP_200_OK)
            allow = policy.field_allowlist(type(obj), request=request)
            return Response({"item": services.to_dict(obj, allow=allow)}, status=status.HTTP_200_OK)
        items = services.list_items(model_key, request=request, filters=filters or {})
        allow = policy.field_allowlist(type(items[0]), request=request) if items else None
        return Response({"items": [services.to_dict(o, allow=allow) for o in items]}, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="wcapi_get_list_query",
        summary="Get model records (GET method)",
        description="Retrieve records from any configured model using query parameters. "
                   "Supports pagination, filtering, and field selection.",
        parameters=[
            OpenApiParameter(name="model_name", type=str, required=True, location=OpenApiParameter.QUERY,
                           description="Model key from WCAPI registry (e.g., 'contact', 'action')"),
            OpenApiParameter(name="id", type=int, required=False, location=OpenApiParameter.QUERY,
                           description="Specific record ID to retrieve (returns single item)"),
            OpenApiParameter(name="fields", type=str, required=False, location=OpenApiParameter.QUERY,
                           description="Comma-separated list of fields to include in response")
        ],
        responses={
            200: WcapiResponseSerializer,
            400: WcapiResponseSerializer,
            401: WcapiResponseSerializer,
        }
    )
    def get(self, request, **kwargs):
        # Only accept 'model_name' query param
        model_key = request.query_params.get("model_name")
        if not model_key:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        record_id = request.query_params.get("id")
        fields = request.query_params.get("fields")
        fields_list = [f.strip() for f in fields.split(",")] if isinstance(fields, str) else None
        return self._handle(model_key, record_id, {}, fields_list, request)

    @extend_schema(
        operation_id="wcapi_get_list_body",
        summary="Get model records (POST method)",
        description="Retrieve records from any configured model using request body. "
                   "Supports advanced filtering and pagination compared to GET method.",
        request=inline_serializer(
            name="GetListRequest",
            fields={
                'model': serializers.CharField(required=True),
                'id': serializers.IntegerField(required=False),
                'filters': serializers.DictField(required=False),
                'fields': serializers.ListField(child=serializers.CharField(), required=False),
                'limit': serializers.IntegerField(required=False, default=25),
                'offset': serializers.IntegerField(required=False, default=0)
            }
        ),
        responses={
            200: WcapiResponseSerializer,
            400: WcapiResponseSerializer,
            401: WcapiResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        # Only accept 'model' in body
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
        record_id = body.get("id")
        filters = body.get("filters") or {}
        fields: Optional[List[str]] = body.get("fields")
        if not model_key:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        return self._handle(model_key, record_id, filters, fields, request)


class WCAPISaveView(APIView):
    """
    Universal POST/PUT/PATCH endpoint for creating and updating records across all models.
    
    Handles both creation of new records and updates to existing ones.
    Uses smart save logic with version control and optimistic locking.
    """
    http_method_names = ["post", "put", "patch", "options", "head"]

    def _handle(self, model_key: Optional[str], record_id: Optional[Any], payload: Dict[str, Any], _fields, request):
        body: Dict[str, Any] = payload or {}
        model = model_key or body.get("model")
        rid = record_id if record_id is not None else body.get("id")
        data = body.get("data") or {}
        if not model or not isinstance(data, dict) or not resolve(model):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pk, action = services.save_item(model, request=request, data=data, id=rid)
        except LookupError:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        status_code = status.HTTP_201_CREATED if action == "created" else status.HTTP_200_OK
        return Response({"id": pk, "action": action}, status=status_code)

    @extend_schema(
        operation_id="wcapi_save_create",
        summary="Create new record",
        description="Create a new record in any configured model using WCAPI registry.",
        request=inline_serializer(
            name="SaveCreateRequest",
            fields={
                'model': serializers.CharField(required=True),
                'data': serializers.DictField(required=True)
            }
        ),
        responses={
            201: WcapiResponseSerializer,
            400: WcapiResponseSerializer,
            401: WcapiResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
        record_id = body.get("id")
        return self._handle(model_key, record_id, body, None, request)

    put = post
    patch = post