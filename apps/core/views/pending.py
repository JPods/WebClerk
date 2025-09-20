from rest_framework import pagination, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F

from apps.core.models import Pending
from apps.core.serializers.pending import PendingSerializer
from common.base_views import BaseListCreateView
from common.http.mixins import BaseJSONAPIView
from common.search_mixins import PrefixAndSearchView


class PendingListView(BaseListCreateView):
    queryset = Pending.objects.all().order_by('-id')
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    class Pagination(pagination.PageNumberPagination):
        page_size = 25
        page_size_query_param = 'page_size'
        max_page_size = 500
    pagination_class = Pagination

class PendingDetail(BaseJSONAPIView):
    pass

class PendingDetailView(BaseJSONAPIView):
    queryset = Pending.objects.all()
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]
    _allow_write = True  # allow WriteGate

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk") or kwargs.get("id")
        obj = get_object_or_404(self.queryset, pk=pk)
        return Response(self.serializer_class(obj).data)

    def patch(self, request, *args, **kwargs):
        pk = kwargs.get("pk") or kwargs.get("id")
        obj = get_object_or_404(self.queryset, pk=pk)

        body = request.data or {}
        req_version = body.get("version")
        if req_version is None:
            return Response({"detail": "Missing version."}, status=400)

        # Atomic CAS: only bump version by exactly +1 if matches request version
        with transaction.atomic():
            rows = Pending.objects.filter(pk=pk, version=req_version).update(
                version=F("version") + 1,
            )
            if rows == 0:
                # Precondition Failed when version doesn't match
                return Response({"detail": "Version conflict."}, status=412)

        obj = Pending.objects.get(pk=pk)
        return Response(self.serializer_class(obj).data)

class PendingSearchView(PrefixAndSearchView):
    queryset = Pending.objects.all()
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['model_name','record_id','ida']
    model = Pending

class PendingViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Pending.objects.all()
    serializer_class = PendingSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk") or kwargs.get("id")
        obj = get_object_or_404(self.queryset, pk=pk)
        return Response(self.serializer_class(obj).data)

    def partial_update(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
