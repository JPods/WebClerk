from rest_framework import generics, permissions, pagination, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import F, Q
from apps.docs.models.document import Document
from apps.docs.serializers.document_serializers import DocumentSerializer, DocumentSearchSerializer


class DocumentPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['modified_dt', 'created_dt', 'name', 'security_level', 'status']
    ordering = ['-modified_dt']

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