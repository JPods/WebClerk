from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from rest_framework.permissions import IsAuthenticated
from rest_framework import pagination
from apps.core.models import Contact
from apps.core.serializers.contact_serializer import ContactSerializer


class ContactListView(BaseListCreateView):
    queryset = Contact.objects.all().order_by('-id')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'contacts'

    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500

    pagination_class = Pagination


class ContactDetailView(BaseOptimisticDetailView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    table_name = 'contacts'


class ContactSearchView(PrefixAndSearchView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    search_fields = [
        'email', 'company', 'title', 'department',
        'name_first', 'name_last', 'ida'
    ]
    table_name = 'contacts'
    model = Contact
