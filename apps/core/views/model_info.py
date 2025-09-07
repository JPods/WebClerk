from rest_framework.views import APIView
from rest_framework.response import Response  # legacy direct
from django.apps import apps
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, to_model_name


class ModelInfoView(APIView):
    def get(self, request):
        raw_name = request.query_params.get('model_name')
        table_name = normalize_table_key(raw_name) if raw_name else None
        related_tables = request.query_params.get('related_tables')
        models_info = {}

        def get_fields(m):
            return [f.name for f in m._meta.fields]

        # Main table info
        if table_name:
            for model in apps.get_models():
                model_db_table = model._meta.db_table
                if model_db_table == table_name:
                    models_info[to_model_name(model_db_table)] = get_fields(model)
                    break
        else:
            for model in apps.get_models():
                model_db_table = model._meta.db_table
                models_info[to_model_name(model_db_table)] = get_fields(model)

        # Related tables info
        if related_tables:
            related_list = [tbl.strip() for tbl in related_tables.split(',') if tbl.strip()]
            for tbl in related_list:
                for model in apps.get_models():
                    if model._meta.db_table == tbl:
                        models_info[to_model_name(tbl)] = get_fields(model)
                        break
        return api_response(data={'models': models_info})