from rest_framework import generics, permissions, pagination, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F, Q
from apps.docs.models.tag import Tag
from apps.docs.serializers.tag_serializers import TagSerializer, TagDetailSerializer

class TagPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200

class TagListCreateView(generics.ListCreateAPIView):
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TagPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['dt_modified','dt_created','name','purpose','status','security_level','sequence']
    ordering = ['-dt_modified']

    def get_queryset(self):
        qs = Tag.objects.filter(is_active=True)  # exclude inactive by default
        purpose = self.request.GET.get('purpose')
        status_val = self.request.GET.get('status')
        level = self.request.GET.get('security_level') or self.request.GET.get('level')
        table = self.request.GET.get('table_name') or self.request.GET.get('table')
        record_id = self.request.GET.get('record_id')
        if self.request.GET.get('include_inactive') in ('1','true','yes'):
            qs = Tag.objects.all()  # override filter
        if purpose:
            qs = qs.filter(purpose=purpose)
        if status_val:
            qs = qs.filter(status=status_val)
        if level is not None:
            try:
                qs = qs.filter(security_level=int(level))
            except ValueError:
                pass
        if table:
            qs = qs.filter(table_name=table)
        if record_id:
            try:
                qs = qs.filter(record_id=int(record_id))
            except ValueError:
                pass
        return qs

class TagRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Tag.objects.filter(is_active=True)
    serializer_class = TagDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        self.get_object().increment_access(by=1, update_history=False)
        return response

class TagHierarchyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # add child
        tag = Tag.objects.filter(pk=pk).first()
        if not tag:
            return Response({'detail':'Not found'}, status=404)
        # Support single child_id or list child_ids
        child_id = request.data.get('child_id')
        child_ids = request.data.get('child_ids') or request.data.get('add_children')
        results = []
        if child_ids and isinstance(child_ids, list):
            for cid in child_ids:
                try:
                    added = tag.add_child(int(cid))
                    results.append({'child_id': cid, 'added': added})
                except Exception:
                    results.append({'child_id': cid, 'added': False, 'error': 'invalid'})
        elif child_id is not None:
            added = tag.add_child(int(child_id))
            results.append({'child_id': int(child_id), 'added': added})
        else:
            return Response({'detail':'child_id or child_ids required'}, status=400)
        tag.save()
        return Response({'results': results, 'children': tag.children_ids()})

    def delete(self, request, pk):
        tag = Tag.objects.filter(pk=pk).first()
        if not tag:
            return Response({'detail':'Not found'}, status=404)
        child_id = request.data.get('child_id') or request.GET.get('child_id')
        child_ids = request.data.get('child_ids') or request.data.get('remove_children')
        results = []
        if child_ids and isinstance(child_ids, list):
            for cid in child_ids:
                try:
                    removed = tag.remove_child(int(cid))
                    results.append({'child_id': cid, 'removed': removed})
                except Exception:
                    results.append({'child_id': cid, 'removed': False, 'error': 'invalid'})
        elif child_id is not None:
            removed = tag.remove_child(int(child_id))
            results.append({'child_id': int(child_id), 'removed': removed})
        else:
            return Response({'detail':'child_id or child_ids required'}, status=400)
        tag.save()
        return Response({'results': results, 'children': tag.children_ids()})

    def patch(self, request, pk):
        # set parent
        tag = Tag.objects.filter(pk=pk).first()
        if not tag:
            return Response({'detail':'Not found'}, status=404)
        parent_id = request.data.get('parent_id')
        tag.set_parent(parent_id if parent_id is None else int(parent_id))
        tag.save()
        return Response({'parent_id': tag.parent_id()})

class TagSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            return Response({'results': [], 'count': 0, 'q': raw_q})
        terms = [t for t in raw_q.split() if t]
        qs = Tag.objects.filter(is_active=True)
        # Optional filters
        purpose = request.GET.get('purpose')
        if purpose:
            qs = qs.filter(purpose=purpose)
        # Build AND chain of prefix filters across name/purpose
        for term in terms:
            qs = qs.filter(Q(name__istartswith=term) | Q(purpose__istartswith=term))
        qs = qs.order_by('-dt_modified')[:100]
        data = TagSerializer(qs, many=True).data
        # Increment access counters
        for tag in qs:
            tag.increment_access(by=1, update_history=False)
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})
