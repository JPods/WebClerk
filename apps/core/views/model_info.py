from rest_framework.views import APIView
from rest_framework.response import Response  # legacy direct
from django.apps import apps
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, to_model_name
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers


class ModelInfoView(APIView):
    @extend_schema(
        operation_id="core_model_info_retrieve",
        parameters=[
            OpenApiParameter(name='model_name', description='Singular model_name code to restrict', required=False, type=str),
            OpenApiParameter(name='related_model_names', description='Comma-separated model_name codes to include', required=False, type=str),
        ],
        responses={
            200: inline_serializer(
                name='ModelInfoResponse',
                fields={'models': serializers.DictField(child=serializers.ListField(child=serializers.CharField()))}
            )
        }
    )
    def get(self, request):
        raw_name = request.query_params.get('model_name')
        model_key = normalize_table_key(raw_name) if raw_name else None
        related_tables = request.query_params.get('related_model_names')
        models_info = {}

        def get_fields(model_obj):
            return [f.name for f in model_obj._meta.fields]

        if model_key:
            for model_obj in apps.get_models():
                if model_obj._meta.db_table == model_key:
                    models_info[to_model_name(model_obj._meta.db_table)] = get_fields(model_obj)
                    break
        else:
            for model_obj in apps.get_models():
                models_info[to_model_name(model_obj._meta.db_table)] = get_fields(model_obj)

        if related_tables:
            related_list = [tbl.strip() for tbl in related_tables.split(',') if tbl.strip()]
            for tbl in related_list:
                for model_obj in apps.get_models():
                    if model_obj._meta.db_table == tbl:
                        models_info[to_model_name(tbl)] = get_fields(model_obj)
                        break
        return api_response(data={'models': models_info})