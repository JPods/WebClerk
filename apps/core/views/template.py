from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from rest_framework import pagination
from apps.core.models.template import Template
from apps.core.serializers.template import TemplateSerializer
from django.db.models import Q  # added

class TemplateListView(BaseListCreateView):
    _allow_write = True  # let WriteGate pass POST
    permission_classes = [IsAuthenticated]
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    # model_name only
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class TemplateDetailView(BaseOptimisticDetailView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]

class TemplateSearchView(PrefixAndSearchView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]
    # Limit to actual model fields to avoid FieldError -> 500
    search_fields = ["name", "purpose"]
    model = Template

    def get_queryset(self):
        qs = Template.objects.all()
        q = self.request.GET.get("q") or ""
        prefix = self.request.GET.get("prefix") or ""
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(purpose__icontains=q))
        if prefix:
            qs = qs.filter(name__istartswith=prefix)
        return qs
