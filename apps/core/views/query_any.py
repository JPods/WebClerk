from rest_framework.views import APIView
from rest_framework.response import Response  # legacy
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
import importlib
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, to_model_name

# Map canonical model keys (plural db_table) to model classes
TABLE_MODEL_MAP = {
    "contacts": "core.models.contact.Contact",
    "actions": "core.models.action.Action",
    "phones": "core.models.phone.Phone",
    "emails": "core.models.email.Email",
    "locations": "communications.models.location.Location",
    # Extend as needed
}

def get_model_class(model_key):
    model_path = TABLE_MODEL_MAP.get(model_key)
    if not model_path:
        return None
    module_path, class_name = model_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

class QueryAnyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_name = request.data.get('model_name')
        model_key = normalize_table_key(raw_name) if raw_name else None
        field = request.data.get('field')
        value = request.data.get('value')
        query_type = request.data.get('query_type', 'exact')  # exact, icontains, etc.
        if not model_key:
            return api_response(success=False, status_code=400, message='Missing model_name', error={'code':'missing_model_name','details':'Missing model_name'})
        if not field:
            return api_response(success=False, status_code=400, message='Missing field', error={'code':'missing_field','details':'Provide field'})
        model_cls = get_model_class(model_key)
        if not model_cls:
            return api_response(success=False, status_code=400, message='Model not found', error={'code':'model_not_found','details':model_key})

        lookup = f"{field}__{query_type}"
        try:
            results = model_cls.objects.filter(**{lookup: value})
            data = [{fld: getattr(obj, fld, None) for fld in [field, 'id']} for obj in results]
            return api_response(data={'model_name': to_model_name(model_key), 'field': field, 'query_type': query_type, 'value': value, 'results': data})
        except Exception as e:
            return api_response(success=False, status_code=400, message='Query failed', error={'code':'query_failed','details': str(e)})