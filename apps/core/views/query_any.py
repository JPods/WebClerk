from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
import importlib

# Map table names to model classes
TABLE_MODEL_MAP = {
    "contacts": "core.models.contact.Contact",
    "actions": "core.models.action.Action",
    "phones": "core.models.phone.Phone",
    "emails": "core.models.email.Email",
    "locations": "communications.models.location.Location",
    # Add more as needed
}

def get_model_class(table_name):
    model_path = TABLE_MODEL_MAP.get(table_name)
    if not model_path:
        return None
    module_path, class_name = model_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

class QueryAnyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        table_name = request.data.get('table_name')
        field = request.data.get('field')
        value = request.data.get('value')
        query_type = request.data.get('query_type', 'exact')  # exact, icontains, etc.

        model_cls = get_model_class(table_name)
        if not model_cls:
            return Response({"success": False, "data": None, "errors": {"message": "Model not found"}})

        # Build filter kwargs
        lookup = f"{field}__{query_type}"
        try:
            results = model_cls.objects.filter(**{lookup: value})
            data = [{f: getattr(obj, f, None) for f in [field, 'id']} for obj in results]
            return Response({"success": True, "data": data, "errors": {}})
        except Exception as e:
            return Response({"success": False, "data": None, "errors": {"message": str(e)}})