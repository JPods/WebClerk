from rest_framework import permissions, pagination, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models

from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from apps.sync.models.connection import Connection
from apps.sync.serializers.connection import ConnectionSerializer

class SyncPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500

class ConnectionListView(BaseListCreateView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    pagination_class = SyncPagination
    ALLOWED_ROLES = {'staff','admin'}

class ConnectionDetailView(BaseOptimisticDetailView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    ALLOWED_ROLES = {'staff','admin'}

class ConnectionSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    ALLOWED_ROLES = {'staff','admin'}

    def get(self, request):
        user = request.user
        if not (getattr(user,'role','') in self.ALLOWED_ROLES or user.is_superuser):
            return Response({'detail':'Forbidden'}, status=403)
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            return Response({'results': [], 'count': 0})
        terms = [t for t in raw_q.split() if t]
        qs = Connection.objects.filter(is_active=True)
        for term in terms:
            qs = qs.filter(
                models.Q(name__icontains=term) | models.Q(type__icontains=term) | models.Q(status__icontains=term)
            )
        qs = qs.order_by('-dt_modified')[:100]
        data = ConnectionSerializer(qs, many=True, context={'request': request}).data
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})
