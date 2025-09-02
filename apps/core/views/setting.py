from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from rest_framework import pagination
from apps.core.models.setting import Setting
from apps.core.serializers.setting import SettingSerializer

class SettingListView(BaseListCreateView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'settings'
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class SettingDetailView(BaseOptimisticDetailView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'settings'

class SettingSearchView(PrefixAndSearchView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name','purpose','table_name','ida']
    table_name = 'settings'
    model = Setting
