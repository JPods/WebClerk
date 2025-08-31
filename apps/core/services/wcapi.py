from django.views import View
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
import json
import time
from .wcapi_registry import get_model, ALLOWED_TABLE_NAMES
from django.db import models
from typing import Sequence
from collections import defaultdict
import os
try:
    # Enable Prometheus if env WCAPI_PROMETHEUS=1 (backward compat: WCAPI_METRICS_BACKEND=prom)
    PROM_ENABLED = os.getenv('WCAPI_PROMETHEUS', '0') == '1' or os.getenv('WCAPI_METRICS_BACKEND') == 'prom'
    if PROM_ENABLED:
        from prometheus_client import Counter, Summary, generate_latest, CONTENT_TYPE_LATEST  # type: ignore
        _PROM_REQS = Counter('wcapi_requests_total', 'Total WCAPI requests', ['method'])
        _PROM_DUR = Summary('wcapi_request_duration_seconds', 'Request duration seconds', ['method'])
    else:
        _PROM_REQS = None  # type: ignore
        _PROM_DUR = None  # type: ignore
except Exception:  # pragma: no cover
    PROM_ENABLED = False
    _PROM_REQS = None  # type: ignore
    _PROM_DUR = None  # type: ignore

"""WcapiView: read/query endpoint over whitelisted models.

Success: {"status":"success","table_name": <str>, "data": [ {...}, ... ]}
Error:   {"status":"error","message": <str>}

Only models registered in wcapi_registry.py are accessible. Filtering is restricted to a
small allow-list to reduce risk of accidental heavy queries or probing internal structure.
"""

SAFE_FILTER_FIELDS = {"email", "name_first", "name_last", "company", "action", "status", "contact_id"}
STRICT_PARAM = 'strict'
STRICT_HEADER = 'HTTP_WCAPI_STRICT'
PROJECTION_PARAM = 'fields'

# In-memory metrics (lightweight; replace with prometheus_client if desired)
_metrics_counters = defaultdict(int)  # key -> count
_metrics_hist_sum = defaultdict(float)  # key -> sum of durations
_metrics_hist_count = defaultdict(int)

def _metric_inc(name: str, labels: dict[str,str]|None=None):
    key = name + ("{"+",".join(f"{k}={v}" for k,v in sorted(labels.items()))+"}" if labels else "")
    _metrics_counters[key] += 1

def _metric_observe(name: str, value: float, labels: dict[str,str]|None=None):
    keybase = name + ("{"+",".join(f"{k}={v}" for k,v in sorted(labels.items()))+"}" if labels else "")
    _metrics_hist_sum[keybase] += value
    _metrics_hist_count[keybase] += 1

def wcapi_metrics_response(_: HttpRequest) -> HttpResponse:
    if PROM_ENABLED and _PROM_REQS is not None:
        try:
            return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)  # type: ignore[arg-type]
        except Exception:
            pass
    lines = ["# HELP wcapi_requests_total Total WCAPI requests", "# TYPE wcapi_requests_total counter"]
    for k,v in sorted(_metrics_counters.items()):
        if k.startswith('wcapi_requests_total'):
            lines.append(f"{k} {v}")
    lines.append("# HELP wcapi_request_duration_seconds Request duration seconds")
    lines.append("# TYPE wcapi_request_duration_seconds summary")
    for k,sumv in sorted(_metrics_hist_sum.items()):
        if k.startswith('wcapi_request_duration_seconds'):
            cnt = _metrics_hist_count[k]
            lines.append(f"{k}_sum {sumv:.6f}")
            lines.append(f"{k}_count {cnt}")
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type='text/plain')
MAX_RESULTS = 50  # hard upper bound per page
DEFAULT_LIMIT = 25

def _pagination_params(request):
    try:
        limit = int(request.GET.get('limit') or request.POST.get('limit') or DEFAULT_LIMIT)
    except Exception:
        limit = DEFAULT_LIMIT
    try:
        offset = int(request.GET.get('offset') or request.POST.get('offset') or 0)
    except Exception:
        offset = 0
    if limit < 1: limit = DEFAULT_LIMIT
    if limit > MAX_RESULTS: limit = MAX_RESULTS
    if offset < 0: offset = 0
    return limit, offset

@method_decorator(csrf_exempt, name='dispatch')
class WcapiView(LoginRequiredMixin, View):
    """Supports GET (single/list) and POST (filtered list). Other verbs 405."""

    _model_field_cache: dict[type, set[str]] = {}

    def _serialize_queryset(self, qs, limit, offset):
        sliced = qs[offset: offset + limit]
        fields = getattr(self, '_requested_fields', None)
        if fields:
            return list(sliced.values(*fields))
        return list(sliced.values())

    def _model_or_400(self, table_name):
        model = get_model(table_name)
        if not model:
            return None, JsonResponse({'status': 'error', 'message': 'Unknown table'}, status=400)
        return model, None

    # GET: optional id for single record, else list
    def get(self, request):
        # Auth: allow either session or JWT; optional strict mode via WCAPI_JWT_ONLY
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        open_read = getattr(settings, 'WCAPI_OPEN_READ', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            if not open_read:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
            # proceed as PUBLIC role (implicit) for open read mode
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return JsonResponse({'status': 'error', 'message': 'JWT Bearer token required'}, status=401)
        start = time.perf_counter()
        table_name = request.GET.get('table_name')
        if not table_name:
            return JsonResponse({'status':'error','message':'Missing table_name'}, status=400)
        model, err = self._model_or_400(table_name)
        if err:
            return err
        # Field projection
        self._requested_fields = self._parse_projection(request, model)
        if isinstance(self._requested_fields, JsonResponse):
            return self._requested_fields  # error response
        record_id = request.GET.get('id')
        if record_id:
            try:
                obj = model.objects.get(id=record_id)  # type: ignore[attr-defined]
            except Exception:
                return JsonResponse({'status':'error','message':'Not found'}, status=404)
            data_obj = obj.__dict__.copy(); data_obj.pop('_state', None)
            if getattr(self, '_requested_fields', None):
                data = [{k: v for k, v in data_obj.items() if k in self._requested_fields}]
            else:
                data = [data_obj]
            _metric_inc('wcapi_requests_total', {'method':'GET'})
            _metric_observe('wcapi_request_duration_seconds', time.perf_counter()-start, {'method':'GET'})
            if PROM_ENABLED and _PROM_REQS is not None and _PROM_DUR is not None:
                _PROM_REQS.labels(method='GET').inc()
                _PROM_DUR.labels(method='GET').observe(time.perf_counter()-start)
            return JsonResponse({'status':'success','table_name':table_name,'data':data})
        qs = model.objects.all()  # type: ignore[attr-defined]
        total = qs.count()
        limit, offset = _pagination_params(request)
        data = self._serialize_queryset(qs, limit, offset)
        _metric_inc('wcapi_requests_total', {'method':'GET'})
        _metric_observe('wcapi_request_duration_seconds', time.perf_counter()-start, {'method':'GET'})
        if PROM_ENABLED and _PROM_REQS is not None and _PROM_DUR is not None:
            _PROM_REQS.labels(method='GET').inc()
            _PROM_DUR.labels(method='GET').observe(time.perf_counter()-start)
        return JsonResponse({'status':'success','table_name':table_name,'data':data,'total':total,'limit':limit,'offset':offset})

    # POST: filtered list (exact match on allow-listed fields)
    def post(self, request):
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        open_read = getattr(settings, 'WCAPI_OPEN_READ', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            if not open_read:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return JsonResponse({'status': 'error', 'message': 'JWT Bearer token required'}, status=401)
        start = time.perf_counter()
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
        self._requested_fields = self._parse_projection(payload, model)
        if isinstance(self._requested_fields, JsonResponse):
            return self._requested_fields  # error response
        qs = model.objects.all()  # type: ignore[attr-defined]
        strict = self._strict_mode(request, payload)
        invalid_filters: list[str] = []
        for k, v in payload.items():
            if k in (PROJECTION_PARAM, 'table_name', 'limit', 'offset', STRICT_PARAM):
                continue
            if k in SAFE_FILTER_FIELDS and hasattr(model, k):
                try:
                    qs = qs.filter(**{k: v})
                except Exception:
                    pass  # ignore bad values
            else:
                if strict and k not in invalid_filters:
                    invalid_filters.append(k)
        if strict and invalid_filters:
            return JsonResponse({'status':'error','message':f"Invalid filter field(s): {', '.join(sorted(invalid_filters))}"}, status=400)
        total = qs.count()
        limit, offset = _pagination_params(request)
        data = self._serialize_queryset(qs, limit, offset)
        _metric_inc('wcapi_requests_total', {'method':'POST'})
        _metric_observe('wcapi_request_duration_seconds', time.perf_counter()-start, {'method':'POST'})
        if PROM_ENABLED and _PROM_REQS is not None and _PROM_DUR is not None:
            _PROM_REQS.labels(method='POST').inc()
            _PROM_DUR.labels(method='POST').observe(time.perf_counter()-start)
        return JsonResponse({'status':'success','table_name':table_name,'data':data,'total':total,'limit':limit,'offset':offset})

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

    # --- helpers ---
    def _parse_projection(self, source, model):
        """Parse requested field projection. Returns list[str] or JsonResponse on error or None if none requested."""
        if isinstance(source, HttpRequest):
            raw = source.GET.get(PROJECTION_PARAM)
        else:
            raw = source.get(PROJECTION_PARAM)
        if not raw:
            return None
        if isinstance(raw, str):
            try:
                # allow comma separated OR JSON list encoded as string
                if raw.strip().startswith('['):
                    fields = json.loads(raw)
                else:
                    fields = [p.strip() for p in raw.split(',') if p.strip()]
            except Exception:
                return JsonResponse({'status':'error','message':'Invalid fields format'}, status=400)
        elif isinstance(raw, (list, tuple)):
            fields = list(raw)
        else:
            return JsonResponse({'status':'error','message':'Invalid fields type'}, status=400)
        # Validate
        cached = self._model_field_cache.get(model)
        if cached is None:
            cached = {f.name for f in model._meta.get_fields() if isinstance(f, models.Field)}
            self._model_field_cache[model] = cached
        model_fields = cached
        invalid = [f for f in fields if f not in model_fields]
        if invalid:
            return JsonResponse({'status':'error','message':f'Invalid field(s): {", ".join(invalid)}'}, status=400)
        # prevent empty
        if not fields:
            return JsonResponse({'status':'error','message':'No fields specified'}, status=400)
        return fields

    def _strict_mode(self, request, payload):
        header = request.META.get(STRICT_HEADER)
        if header and str(header).lower() in {'1','true','yes'}:
            return True
        flag = None
        if request.method == 'GET':
            flag = request.GET.get(STRICT_PARAM)
        else:
            if isinstance(payload, dict):
                flag = payload.get(STRICT_PARAM)
        return str(flag).lower() in {'1','true','yes'}



