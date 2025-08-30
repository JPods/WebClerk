from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from rest_framework import pagination
from rest_framework.permissions import IsAuthenticated
from apps.core.models.action import Action
from apps.core.serializers.action import ActionSerializer

class ActionListView(BaseListCreateView):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'actions'
    ALLOWED_ROLES = {'staff','admin'}
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class ActionDetailView(BaseOptimisticDetailView):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'actions'
    ALLOWED_ROLES = {'staff','admin'}

class ActionSearchView(PrefixAndSearchView):
    model = Action
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['action','status','action_by','priority','ida']
    role_set = {'staff','admin'}
