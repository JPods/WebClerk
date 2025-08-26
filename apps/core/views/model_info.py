from rest_framework.views import APIView
from rest_framework.response import Response
from django.apps import apps

class ModelInfoView(APIView):
    def get(self, request):
        table_name = request.query_params.get('table_name')
        related_tables = request.query_params.get('related_tables')
        models_info = {}

        def get_fields(model):
            return [f.name for f in model._meta.fields]

        # Main table info
        if table_name:
            for model in apps.get_models():
                model_db_table = model._meta.db_table
                if model_db_table == table_name:
                    models_info[model_db_table] = get_fields(model)
                    break
        else:
            for model in apps.get_models():
                model_db_table = model._meta.db_table
                models_info[model_db_table] = get_fields(model)

        # Related tables info
        if related_tables:
            related_list = [tbl.strip() for tbl in related_tables.split(',') if tbl.strip()]
            for tbl in related_list:
                for model in apps.get_models():
                    if model._meta.db_table == tbl:
                        models_info[tbl] = get_fields(model)
                        break

        return Response({"success": True, "models": models_info})