from rest_framework.views import APIView
from common.api_responses import api_response
from apps.core.constants.table_registry import TABLE_REGISTRY, get_table_meta
from django.http import Http404
from apps.core.views.table_registry_view import _serialize_table_meta


def _to_singular_code(key: str) -> str:
    return key[:-1] if key.endswith('s') else key


class ModelNameListView(APIView):
    """Return the list of canonical singular model_name codes."""

    def get(self, request):  # type: ignore[override]
        names = sorted({_to_singular_code(k) for k in TABLE_REGISTRY.keys()})
        return api_response(data={'model_names': names, 'count': len(names)})


class ModelNameDetailView(APIView):
    """Return detail for a given model_name (singular code), including fields."""

    def get(self, request):  # type: ignore[override]
        model_name = (request.query_params.get('model_name') or '').strip().lower()
        if not model_name:
            raise Http404('model_name required')
        # Map singular code back to registry key
        candidates = [model_name, model_name + 's']
        key = next((k for k in candidates if k in TABLE_REGISTRY), None)
        if not key:
            raise Http404('Unknown model_name')
        meta = get_table_meta(key)
        if not meta:
            raise Http404('Unknown model_name')
        payload = _serialize_table_meta(meta, include_fields=True)
        payload['model_name'] = _to_singular_code(key)
        return api_response(data={'model': payload})
