from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from rest_framework import pagination
from apps.core.models.template import Template
from apps.core.serializers.template import TemplateSerializer

class TemplateListView(BaseListCreateView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'templates'
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class TemplateDetailView(BaseOptimisticDetailView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'templates'

class TemplateSearchView(PrefixAndSearchView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name','purpose','table_name','ida']
    table_name = 'templates'
    model = Template
