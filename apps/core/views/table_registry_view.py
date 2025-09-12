from rest_framework.views import APIView
from common.api_responses import api_response
from apps.core.constants.model_registry import (
    MODEL_REGISTRY, get_model_meta, get_model_meta_by_endpoint
)
from django.http import Http404

def _serialize_table_meta(meta, include_fields: bool = False):
    base = {
        'key': meta.key,
        'model': meta.model,
        'singular': meta.singular,
        'plural': meta.plural,
        'endpoint': meta.endpoint,
        'kind': meta.kind,
    }
    if not include_fields:
        return base
    try:  # dynamic import + field introspection
        model_cls = meta.import_model()
        field_block = {}
        for f in getattr(model_cls._meta, 'concrete_fields', []):  # only concrete db columns
            info = {
                'type': f.get_internal_type(),
                'null': getattr(f, 'null', False),
                'blank': getattr(f, 'blank', False),
                'primary_key': getattr(f, 'primary_key', False),
            }
            choices = getattr(f, 'choices', None)
            if choices:
                # represent as list of {value,label}
                info['choices'] = [{'value': c[0], 'label': c[1]} for c in choices]
            field_block[f.name] = info
        base['fields'] = field_block
    except Exception as e:  # pragma: no cover - defensive path
        base['fields_error'] = str(e)
    return base


class TableRegistryView(APIView):
    """Return canonical table registry metadata.

    List mode (default): GET /wcapi/tables/ -> {tables:{ key: {...basic meta...}}}
    Detail mode: GET /wcapi/tables/?table=<key> OR ?endpoint=<slug>&include_fields=1
      Returns single table payload including field metadata & choices when requested.
    """

    def get(self, request):  # type: ignore[override]
        table_key = request.query_params.get('table')
        endpoint = request.query_params.get('endpoint')
        include_fields = request.query_params.get('include_fields') in ('1', 'true', 'yes')

        if table_key or endpoint:
            meta = None
            if table_key:
                meta = get_model_meta(table_key)
            elif endpoint:
                meta = get_model_meta_by_endpoint(endpoint)
            if not meta:
                raise Http404('Table not found')
            return api_response(data={'table': _serialize_table_meta(meta, include_fields=include_fields)})

        # list mode
        payload = {
            key: _serialize_table_meta(meta, include_fields=False)
            for key, meta in MODEL_REGISTRY.items()
        }
        return api_response(data={'tables': payload})
