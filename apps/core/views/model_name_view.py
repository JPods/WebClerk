from rest_framework.views import APIView
from common.api_responses import api_response
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from django.http import Http404
from apps.core.views.table_registry_view import _serialize_table_meta
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers


def _to_singular_code(key: str) -> str:
    return key[:-1] if key.endswith('s') else key


class ModelNameListView(APIView):
    """Return the list of canonical singular model_name codes."""

    @extend_schema(
        operation_id="core_model_names_list",
        responses={
            200: inline_serializer(name='ModelNameList', fields={
                'model_names': serializers.ListField(child=serializers.CharField()),
                'count': serializers.IntegerField(),
            })
        }
    )
    def get(self, request):  # type: ignore[override]
        names = sorted(MODEL_REGISTRY.keys())
        return api_response(data={'model_names': names, 'count': len(names)})


class ModelNameDetailView(APIView):
    """Return detail for a given model_name (singular code), including fields."""

    @extend_schema(
        operation_id="core_model_name_detail_retrieve",
        parameters=[OpenApiParameter(name='model_name', required=True, type=str)],
        responses={200: inline_serializer(name='ModelNameDetail', fields={'model': serializers.DictField()})}
    )
    def get(self, request):  # type: ignore[override]
        model_name = (request.query_params.get('model_name') or '').strip().lower()
        if not model_name:
            raise Http404('model_name required')
        # Resolve using canonical/aliases/endpoints
        meta = get_model_meta(model_name)
        if not meta:
            raise Http404('Unknown model_name')
        payload = _serialize_table_meta(meta, include_fields=True)
        payload['model_name'] = meta.key
        return api_response(data={'model': payload})
