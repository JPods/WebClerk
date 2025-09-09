from rest_framework.views import APIView
from rest_framework.response import Response  # legacy direct usage (will wrap)
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from common.api_responses import api_response

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
    import importlib
    model_path = TABLE_MODEL_MAP.get(model_key)
    if not model_path:
        return None
    module_path, class_name = model_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

class KeywordSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        keywords_raw = request.data.get('keywords', '')
        model_key = request.data.get('model_name', '')  # accept singular or plural key
        query_type = request.data.get('query_type', 'AND').upper()

        keywords = [kw.strip() for kw in keywords_raw.split(',') if kw.strip()]
        if not keywords:
            return api_response(success=False, status_code=400, message='No keywords provided', error={'code':'no_keywords','details':'No keywords provided'})

        q_obj = Q()
        if query_type == 'OR':
            for kw in keywords:
                q_obj |= Q(refs__keywords__icontains=kw)
        else:  # AND
            for kw in keywords:
                q_obj &= Q(refs__keywords__icontains=kw)

        results = []
        errors = {}

        if model_key == "give_me_all":
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
            model_cls = get_model_class(model_key)
            if model_cls:
                qs = model_cls.objects.filter(q_obj)
                results = [
                    {"table": model_key, "id": obj.id, "keywords": obj.refs.get("keywords", [])}
                    for obj in qs
                ]
            else:
                errors[model_key] = "Model not found"

        payload = {
            'model_name': model_key,
            'query_type': query_type,
            'keywords': keywords,
            'results': results,
        }
        if errors:
            payload['errors'] = errors  # non-fatal per-table errors
        return api_response(data=payload)