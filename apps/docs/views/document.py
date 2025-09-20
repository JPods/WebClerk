from common.base_views import BaseListCreateView, BaseOptimisticDetailView
# QQQ need to implement role-based permissions
from rest_framework.permissions import AllowAny
from apps.docs.models.document import Document
from apps.docs.serializers.document import DocumentSerializer

class DocumentListView(BaseListCreateView):
    _allow_write = True
    permission_classes = [AllowAny]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer