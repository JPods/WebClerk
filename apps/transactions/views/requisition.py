from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from rest_framework import pagination
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from apps.transactions.models.requisition import RequisitionStd
from apps.transactions.serializers.requisition import RequisitionSerializer

class RequisitionListView(BaseListCreateView):
    queryset = RequisitionStd.objects.all()
    serializer_class = RequisitionSerializer
    permission_classes = [IsAuthenticated]
    model_name = 'requisition'
    ALLOWED_ROLES = {'staff','admin'}
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class RequisitionDetailView(BaseOptimisticDetailView):
    queryset = RequisitionStd.objects.all()
    serializer_class = RequisitionSerializer
    permission_classes = [IsAuthenticated]
    model_name = 'requisition'
    ALLOWED_ROLES = {'staff','admin'}

class RequisitionSearchView(PrefixAndSearchView):
    model = RequisitionStd
    serializer_class = RequisitionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name','purpose','status','ida']
    role_set = {'staff','admin'}
