from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

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
    import importlib
    model_path = TABLE_MODEL_MAP.get(table_name)
    if not model_path:
        return None
    module_path, class_name = model_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

class KeywordSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        keywords_raw = request.data.get('keywords', '')
        table_name = request.data.get('table_name', '')
        query_type = request.data.get('query_type', 'AND').upper()

        keywords = [kw.strip() for kw in keywords_raw.split(',') if kw.strip()]
        if not keywords:
            return Response({"success": False, "data": None, "errors": {"message": "No keywords provided"}})

        q_obj = Q()
        if query_type == 'OR':
            for kw in keywords:
                q_obj |= Q(refs__keywords__icontains=kw)
        else:  # AND
            for kw in keywords:
                q_obj &= Q(refs__keywords__icontains=kw)

        results = []
        errors = {}

        if table_name == "give_me_all":
            for tbl, model_path in TABLE_MODEL_MAP.items():
                model_cls = get_model_class(tbl)
                if model_cls:
                    qs = model_cls.objects.filter(q_obj)
                    results.extend([
                        {"table": tbl, "id": obj.id, "keywords": obj.refs.get("keywords", [])}
                        for obj in qs
                    ])
                else:
                    errors[tbl] = "Model not found"
        else:
            model_cls = get_model_class(table_name)
            if model_cls:
                qs = model_cls.objects.filter(q_obj)
                results = [
                    {"table": table_name, "id": obj.id, "keywords": obj.refs.get("keywords", [])}
                    for obj in qs
                ]
            else:
                errors[table_name] = "Model not found"

        return Response({"success": True, "data": results, "errors": errors})