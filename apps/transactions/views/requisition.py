from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.decorators import allow_write
from rest_framework import pagination
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from apps.transactions.models import Requisition  # use package-level alias
from apps.transactions.serializers.requisition import RequisitionSerializer

@allow_write
class RequisitionListView(BaseListCreateView):
    queryset = Requisition.objects.all()
    serializer_class = RequisitionSerializer
    permission_classes = [IsAuthenticated]
    model_name = 'requisition'
    ALLOWED_ROLES = {'staff','admin'}
    class Pagination(pagination.PageNumberPagination):
        pass
    pagination_class = Pagination

@allow_write
class RequisitionDetailView(BaseOptimisticDetailView):
    queryset = Requisition.objects.all()
    serializer_class = RequisitionSerializer


class RequisitionSearchView(PrefixAndSearchView):
    model = Requisition
    serializer_class = RequisitionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name','purpose','status','ida']
    role_set = {'staff','admin'}
