from rest_framework import generics, permissions, pagination, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.management import call_command
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import connection
from django.contrib.postgres import search as pg_search
try:
    # Django 5+ provides SearchHeadline; type ignore for older stubs
    SearchHeadline = pg_search.SearchHeadline  # type: ignore[attr-defined]
except AttributeError:  # Fallback for older Django versions without SearchHeadline
    from django.db import models
    from django.db.models import Func, Value, F as _F
    from typing import ClassVar

    class SearchHeadline(Func):
        function = 'ts_headline'
        # Define output_field at the class level to satisfy both Django and type checkers
        output_field: ClassVar[models.TextField] = models.TextField()

        def __init__(self, expression, query, start_sel='<mark>', stop_sel='</mark>', **extra):
            # Allow passing field name as string
            expr = _F(expression) if isinstance(expression, str) else expression
            options = f"StartSel={start_sel}, StopSel={stop_sel}"
            # Pass output_field explicitly for clarity with type checkers
            super().__init__(Value('english'), expr, query, Value(options), output_field=self.output_field, **extra)
from django.db.models import F, Q, Func, Value
from apps.docs.models.document import Document
from django.utils.http import http_date
from django.utils import timezone
import hashlib
import threading
try:  # optional dependency
    from markdown import markdown as md_to_html  # type: ignore
except Exception:  # fallback if markdown not installed
    def md_to_html(text: str) -> str:  # type: ignore
        return text  # degrade gracefully
from pathlib import Path
from django.conf import settings
import io
import re
from apps.docs.serializers.document_serializers import (
    DocumentSerializer,
    DocumentSearchSerializer,
    DocumentReadmeListSerializer,
    DocumentReadmeDetailSerializer,
)


class DocumentPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['dt_modified', 'dt_created', 'name', 'security_level', 'status']
    ordering = ['-dt_modified']

    def get_queryset(self):
        qs = Document.objects.all()
        status_val = self.request.GET.get('status')
        level = self.request.GET.get('security_level') or self.request.GET.get('level')
        if status_val:
            qs = qs.filter(status=status_val)
        if level is not None:
            try:
                qs = qs.filter(security_level=int(level))
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.rebuild_search_vector(commit=False)


class DocumentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # increment access counter
        obj: Document = self.get_object()
        obj.increment_access(by=1, update_history=False)
        return response

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.rebuild_search_vector(commit=False)


class DocumentSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_q = request.GET.get('q', '').strip()
        level = request.GET.get('security_level') or request.GET.get('level')
        status_val = request.GET.get('status')
        if not raw_q:
            return Response({'results': [], 'count': 0, 'q': raw_q})

        terms = [t for t in raw_q.split() if t]
        if not terms:
            return Response({'results': [], 'count': 0, 'q': raw_q})

        # Build combined query: AND all terms (prefix matching via :*)
        combined_query = None
        for term in terms:
            qobj = SearchQuery(term + ':*', search_type='raw')
            combined_query = qobj if combined_query is None else combined_query & qobj

        base_qs = Document.objects.all()
        if status_val:
            base_qs = base_qs.filter(status=status_val)
        if level is not None:
            try:
                base_qs = base_qs.filter(security_level=int(level))
            except ValueError:
                pass

        if combined_query is None:
            return Response({'results': [], 'count': 0, 'q': raw_q, 'terms': []})

        qs = base_qs.annotate(
            rank=SearchRank(F('search_vector'), combined_query),
            highlight_snippet=SearchHeadline('body', combined_query, start_sel='<mark>', stop_sel='</mark>')
        ).filter(search_vector=combined_query).order_by('-rank')[:100]

        # increment access counts for returned docs
        for doc in qs:
            doc.increment_access(by=1, update_history=False)

        data = DocumentSearchSerializer(qs, many=True).data
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})


class ReadmeIndexView(generics.ListAPIView):
    """Lightweight list of readme documents (slug + summary).

    Criteria: status in ('published','internal','draft') and table_name='readme' OR data.category='readme'.
    """
    serializer_class = DocumentReadmeListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Document.objects.all()
        # Heuristic: readme marker
        qs = qs.filter(
            Q(table_name='readme') | Q(data__category='readme') | Q(name__iendswith='.md')
        )
        level = self.request.GET.get('level') or self.request.GET.get('security_level')
        if level is not None:
            try:
                qs = qs.filter(security_level__lte=int(level))
            except ValueError:
                pass
        return qs.order_by('slug','name')


class ReadmeDetailView(generics.RetrieveAPIView):
    """Retrieve full readme by slug (body returned)."""
    serializer_class = DocumentReadmeDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    queryset = Document.objects.all()

    def get_queryset(self):
        qs = super().get_queryset().filter(
            Q(table_name='readme') | Q(data__category='readme') | Q(name__iendswith='.md')
        )
        level = self.request.GET.get('level') or self.request.GET.get('security_level')
        if level is not None:
            try:
                qs = qs.filter(security_level__lte=int(level))
            except ValueError:
                pass
        return qs

    def retrieve(self, request, *args, **kwargs):
        obj: Document = self.get_object()
        # Conditional ETag / Last-Modified support
        body = obj.body or ''
        checksum = (obj.data or {}).get('checksum') or hashlib.sha256(body.encode('utf-8')).hexdigest()
        etag = f"W/\"{checksum[:32]}\""
        try:
            if hasattr(obj, 'dt_modified') and obj.dt_modified and hasattr(obj.dt_modified, 'timestamp'):
                lm = http_date(int(obj.dt_modified.timestamp()))
            else:
                lm = http_date(int(timezone.now().timestamp()))
        except Exception:
            lm = http_date(int(timezone.now().timestamp()))
        if_none_match = request.headers.get('If-None-Match')
        if_modified_since = request.headers.get('If-Modified-Since')
        if if_none_match == etag or (if_modified_since and if_modified_since == lm):
            # Not modified
            resp = Response(status=status.HTTP_304_NOT_MODIFIED)
            resp['ETag'] = etag
            resp['Last-Modified'] = lm
            return resp
        response = super().retrieve(request, *args, **kwargs)
        obj.increment_access(by=1, update_history=False)
        response['ETag'] = etag
        response['Last-Modified'] = lm
        # cache headers (soft: private so browser can store per-user)
        max_age = getattr(settings, 'README_CACHE_SECONDS', 60)
        response['Cache-Control'] = f"private, max-age={max_age}"
        response['X-Readme-Access-Count'] = str(obj.count_accessed)
        # Optional HTML render (cached in data)
        try:
            if isinstance(obj.data, dict) and 'html' not in obj.data:
                html = md_to_html(body)
                if len(html.encode('utf-8')) < 500_000:
                    obj.data['html'] = html
                    Document.objects.filter(pk=obj.pk).update(data=obj.data)
            # Envelope may have wrapped response; attempt nested injection
            if hasattr(response, 'data') and isinstance(response.data, dict):
                payload = response.data.get('data') if 'data' in response.data else response.data
                if isinstance(payload, dict):
                    payload['html'] = (obj.data or {}).get('html')
                    if 'data' in response.data and isinstance(response.data['data'], dict):
                        response.data['data'] = payload
        except Exception:
            pass
        return response


# --- In-memory readme index search (lightweight) ----------------------------
_index_cache_lock = threading.Lock()
_index_cache: list[dict] | None = None
_index_cache_mtime: float | None = None


def _load_index_if_needed(path: str = 'docs_index.json') -> list[dict]:
    global _index_cache, _index_cache_mtime
    p = Path(path)
    if not p.exists():
        return []
    stat = p.stat()
    with _index_cache_lock:
        if _index_cache is None or _index_cache_mtime != stat.st_mtime:
            try:
                import json
                _index_cache = json.loads(p.read_text(encoding='utf-8'))
                _index_cache_mtime = stat.st_mtime
            except Exception:
                _index_cache = []
        return _index_cache or []


class ReadmeSearchIndexView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = (request.GET.get('q') or '').strip().lower()
        limit = min(int(request.GET.get('limit', 25)), 200)
        fuzzy_requested = (request.GET.get('fuzzy') or '').lower() in {'1','true','yes','on'}
        index = _load_index_if_needed()
        if not q:
            return Response({'results': index[:limit], 'count': len(index), 'q': q, 'cache': bool(index)})
        terms = [t for t in q.split() if t]
        results: list[dict] = []
        for rec in index:
            hay = ' '.join([rec.get('slug',''), rec.get('title',''), ' '.join(rec.get('headings', []))]).lower()
            if all(t in hay for t in terms):
                results.append(rec)
                if len(results) >= limit:
                    break
        fuzzy_info = None
        if (fuzzy_requested or not results) and terms and connection.vendor == 'postgresql':
            try:
                from django.contrib.postgres.search import TrigramSimilarity  # type: ignore
                from functools import reduce
                from django.db.models import Q
                q_filter = reduce(lambda acc, t: acc | Q(name__icontains=t) | Q(description__icontains=t) | Q(body__icontains=t), terms[1:], Q(name__icontains=terms[0]) | Q(description__icontains=terms[0]) | Q(body__icontains=terms[0]))
                # Build similarity expression sum
                sim_expr = None
                for t in terms:
                    part = TrigramSimilarity('name', t) + TrigramSimilarity('description', t)
                    sim_expr = part if sim_expr is None else sim_expr + part
                qs = Document.objects.filter(
                    (Q(table_name='readme') | Q(data__category='readme') | Q(name__iendswith='.md')) & q_filter
                ).annotate(trigram=sim_expr).order_by('-trigram')[:limit]
                seen = {r.get('slug') for r in results}
                trigram_results = []
                for doc in qs:
                    if doc.slug in seen:
                        continue
                    trigram_results.append({
                        'slug': doc.slug,
                        'title': doc.name,
                        'score': getattr(doc, 'trigram', 0),
                        'match_type': 'trigram',
                        'headings': (doc.data or {}).get('headings') or []
                    })
                if trigram_results:
                    remaining = max(0, limit - len(results))
                    results.extend(trigram_results[:remaining])
                    fuzzy_info = {'fuzzy_applied': True, 'trigram': True, 'fuzzy_candidates': len(trigram_results)}
            except Exception:
                pass
        # Python fallback if still empty or fuzzy explicitly requested
        if (fuzzy_requested or not results) and terms and fuzzy_info is None:
            def _lev(a: str, b: str) -> int:
                if a == b:
                    return 0
                la, lb = len(a), len(b)
                if la == 0:
                    return lb
                if lb == 0:
                    return la
                prev = list(range(lb + 1))
                for i, ca in enumerate(a, 1):
                    cur = [i]
                    for j, cb in enumerate(b, 1):
                        cost = 0 if ca == cb else 1
                        cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost))
                    prev = cur
                return prev[-1]
            def _similarity(a: str, b: str) -> float:
                m = max(len(a), len(b)) or 1
                return 1.0 - (_lev(a, b) / m)
            scored: list[tuple[float, dict]] = []
            term_threshold = 0.68
            for rec in index:
                hay_tokens = {t for t in (rec.get('slug','') + ' ' + rec.get('title','') + ' ' + ' '.join(rec.get('headings', []))).lower().split() if t}
                term_scores = []
                for t in terms:
                    best = 0.0
                    for tok in hay_tokens:
                        if tok and t and tok[0] != t[0] and abs(len(tok)-len(t)) > 2:
                            continue
                        sim = _similarity(t, tok)
                        if sim > best:
                            best = sim
                        if best == 1.0:
                            break
                    if best >= term_threshold:
                        term_scores.append(best)
                    else:
                        term_scores = []
                        break
                if term_scores:
                    scored.append((sum(term_scores)/len(term_scores), rec))
            already_ids = {id(r) for r in results}
            fuzzy_sorted = [r for score, r in sorted(scored, key=lambda x: x[0], reverse=True) if id(r) not in already_ids]
            if fuzzy_sorted:
                score_map = {id(rec): score for score, rec in scored}
                annotated = []
                for r in fuzzy_sorted:
                    r_copy = dict(r)
                    r_copy['score'] = round(score_map[id(r)],4)
                    r_copy['match_type'] = 'fuzzy'
                    annotated.append(r_copy)
                remaining = max(0, limit - len(results))
                results.extend(annotated[:remaining])
                fuzzy_info = {'fuzzy_applied': True, 'fuzzy_candidates': len(fuzzy_sorted)}
            else:
                fuzzy_info = {'fuzzy_applied': True, 'fuzzy_candidates': 0}
        payload = {'results': results, 'count': len(results), 'q': q, 'terms': terms}
        if fuzzy_info:
            payload.update(fuzzy_info)
        payload['fuzzy_requested'] = fuzzy_requested
        return Response(payload)


class ReadmeTopView(generics.ListAPIView):
    """Return top accessed readmes (default 10)."""
    serializer_class = DocumentReadmeListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        limit = 10
        try:
            limit = min(int(self.request.GET.get('limit', 10)), 100)
        except ValueError:
            pass
        qs = Document.objects.filter(
            Q(table_name='readme') | Q(data__category='readme') | Q(name__iendswith='.md')
        ).order_by('-count_accessed', 'slug')
        return qs[:limit]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        max_age = getattr(settings, 'README_INDEX_CACHE_SECONDS', 120)
        response['Cache-Control'] = f"private, max-age={max_age}"
        return response


class ReadmeSyncView(APIView):
    """Admin-only endpoint to run the sync_readmes command.

    Query params mapped to management options:
    - root: can be provided multiple times to include additional roots
    - delete_missing: '1'/'true' to enable deletions
    - dry_run: '1'/'true' dry run
    - force, allow_empty, export_index, truncate: '1'/'true'
    - max_bytes: integer, index_path: string
    - modified_since: epoch ms or YYYY-MM-DDTHH:MM:SSZ
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        params = request.query_params
        def as_bool(key: str) -> bool:
            val = (params.get(key) or '').lower()
            return val in {"1", "true", "yes", "on"}

        opts: dict = {}
        # Repeatable params
        roots = params.getlist('root') if hasattr(params, 'getlist') else []
        if roots:
            opts['root'] = roots
        # Simple flags
        for flag in ['delete_missing', 'dry_run', 'force', 'allow_empty', 'export_index', 'truncate']:
            if as_bool(flag):
                opts[flag] = True
        # Scalars
        if params.get('max_bytes'):
            try:
                opts['max_bytes'] = int(params.get('max_bytes'))
            except Exception:
                pass
        if params.get('modified_since'):
            opts['modified_since'] = params.get('modified_since')
        if params.get('index_path'):
            opts['index_path'] = params.get('index_path')

        buf = io.StringIO()
        try:
            call_command('sync_readmes', stdout=buf, stderr=buf, **opts)
        except Exception as exc:
            return Response({'ok': False, 'error': str(exc), 'opts': opts}, status=status.HTTP_400_BAD_REQUEST)

        out = buf.getvalue()
        # Parse summary line if present
        stats = {}
        m = re.search(r"Created=(?P<created>\d+) Updated=(?P<updated>\d+) Unchanged=(?P<unchanged>\d+) Discovered=(?P<discovered>\d+)", out)
        if m:
            stats = {k: int(v) for k, v in m.groupdict().items()}
        payload = {
            'ok': True,
            'stats': stats,
            'opts': opts,
        }
        # Avoid returning potentially long stdout unless requested
        if as_bool('include_output'):
            payload['output'] = out[-5000:]
        return Response(payload)