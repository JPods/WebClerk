from rest_framework import generics, pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Pending
from apps.core.serializers.pending import PendingSerializer
from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView


class PendingListView(BaseListCreateView):
    queryset = Pending.objects.all().order_by('-id')
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'pending'
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination


class PendingDetailView(BaseOptimisticDetailView):
    queryset = Pending.objects.all()
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'pending'
    # disable atomic JSON operations (SlimBaseModel lacks metadata/refs JSON envelopes)
    atomic_keys = ()


class PendingSearchView(PrefixAndSearchView):
    queryset = Pending.objects.all()
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['table_name','record_id','ida']
    table_name = 'pending'
    model = Pending
