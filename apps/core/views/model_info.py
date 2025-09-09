from rest_framework.views import APIView
from rest_framework.response import Response  # legacy direct
from django.apps import apps
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, to_model_name


class ModelInfoView(APIView):
    def get(self, request):
        raw_name = request.query_params.get('model_name')
        model_key = normalize_table_key(raw_name) if raw_name else None
        related_tables = request.query_params.get('related_tables')
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