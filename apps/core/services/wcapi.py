from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from .wcapi_registry import get_model, ALLOWED_TABLE_NAMES

"""WcapiView: read/query endpoint over whitelisted models.

Success: {"status":"success","table_name": <str>, "data": [ {...}, ... ]}
Error:   {"status":"error","message": <str>}

Only models registered in wcapi_registry.py are accessible. Filtering is restricted to a
small allow-list to reduce risk of accidental heavy queries or probing internal structure.
"""

SAFE_FILTER_FIELDS = {"email", "name_first", "name_last", "company", "action", "status"}
MAX_RESULTS = 50

@method_decorator(csrf_exempt, name='dispatch')
class WcapiView(LoginRequiredMixin, View):
    """Supports GET (single/list) and POST (filtered list). Other verbs 405."""

    def _serialize_queryset(self, qs):
        return list(qs.values()[:MAX_RESULTS])

    def _model_or_400(self, table_name):
        model = get_model(table_name)
        if not model:
            return None, JsonResponse({'status': 'error', 'message': 'Unknown table'}, status=400)
        return model, None

    # GET: optional id for single record, else list
    def get(self, request):
        table_name = request.GET.get('table_name')
        if not table_name:
            return JsonResponse({'status':'error','message':'Missing table_name'}, status=400)
        model, err = self._model_or_400(table_name)
        if err:
            return err
        record_id = request.GET.get('id')
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:
                return JsonResponse({'status':'error','message':'Not found'}, status=404)
            data = obj.__dict__.copy(); data.pop('_state', None)
            return JsonResponse({'status':'success','table_name':table_name,'data':[data]})
        qs = model.objects.all()
        return JsonResponse({'status':'success','table_name':table_name,'data':self._serialize_queryset(qs)})

    # POST: filtered list (exact match on allow-listed fields)
    def post(self, request):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'status':'error','message':'Invalid JSON'}, status=400)
        table_name = payload.get('table_name')
        if not table_name:
            return JsonResponse({'status':'error','message':'Missing table_name'}, status=400)
        model, err = self._model_or_400(table_name)
        if err:
            return err
        qs = model.objects.all()
        for k, v in payload.items():
            if k in SAFE_FILTER_FIELDS and hasattr(model, k):
                try:
                    qs = qs.filter(**{k: v})
                except Exception:
                    pass  # ignore bad filter values
        return JsonResponse({'status':'success','table_name':table_name,'data':self._serialize_queryset(qs)})

    # Unimplemented verbs -> explicit 405 or minimal info
    def delete(self, request):
        return JsonResponse({'status':'error','message':'DELETE not supported'}, status=405)
    def put(self, request):
        return JsonResponse({'status':'error','message':'PUT not supported'}, status=405)
    def patch(self, request):
        return JsonResponse({'status':'error','message':'PATCH not supported'}, status=405)
    def head(self, request):
        return self.get(request)
    def options(self, request):
        return JsonResponse({'status':'success','data':sorted(ALLOWED_TABLE_NAMES)})
    def trace(self, request):
        return JsonResponse({'status':'error','message':'TRACE not supported'}, status=405)
    def connect(self, request):
        return JsonResponse({'status':'error','message':'CONNECT not supported'}, status=405)
    def manage(self, request):
        return JsonResponse({'status':'error','message':'MANAGE not supported'}, status=405)



