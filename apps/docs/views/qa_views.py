from rest_framework import generics, permissions, pagination, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.contrib.postgres import search as pg_search
try:
    SearchHeadline = pg_search.SearchHeadline  # type: ignore[attr-defined]
except AttributeError:  # Fallback
    from django.db import models
    from django.db.models import Func, Value, F as _F
    from typing import ClassVar
    class SearchHeadline(Func):
        function = 'ts_headline'
        output_field: ClassVar[models.TextField] = models.TextField()
        def __init__(self, expression, query, start_sel='<mark>', stop_sel='</mark>', **extra):
            expr = _F(expression) if isinstance(expression, str) else expression
            options = f"StartSel={start_sel}, StopSel={stop_sel}"
            super().__init__(Value('english'), expr, query, Value(options), output_field=self.output_field, **extra)
from django.db.models import F
from apps.docs.models.qa import Qa
from apps.docs.serializers.qa_serializers import QASerializer, QASearchSerializer

class QAPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200

class QAListCreateView(generics.ListCreateAPIView):
    serializer_class = QASerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = QAPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['dt_modified','dt_created','sequence','security_level','status']
    ordering = ['-dt_modified']

    def get_queryset(self):
        qs = Qa.objects.all()
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

class QARetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Qa.objects.all()
    serializer_class = QASerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        obj: Qa = self.get_object()
        obj.increment_access(by=1, update_history=False)
        return response

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.rebuild_search_vector(commit=False)

class QASearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_q = request.GET.get('q','').strip()
        level = request.GET.get('security_level') or request.GET.get('level')
        status_val = request.GET.get('status')
        if not raw_q:
            return Response({'results': [], 'count': 0, 'q': raw_q})
        terms = [t for t in raw_q.split() if t]
        if not terms:
            return Response({'results': [], 'count': 0, 'q': raw_q})
        combined_query = None
        for term in terms:
            qobj = SearchQuery(term + ':*', search_type='raw')
            combined_query = qobj if combined_query is None else combined_query & qobj
        base_qs = Qa.objects.all()
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
            highlight_snippet=SearchHeadline('answer', combined_query, start_sel='<mark>', stop_sel='</mark>')
        ).filter(search_vector=combined_query).order_by('-rank')[:100]
        for qa in qs:
            qa.increment_access(by=1, update_history=False)
        data = QASearchSerializer(qs, many=True).data
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})
