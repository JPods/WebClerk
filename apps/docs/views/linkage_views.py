from rest_framework import generics, permissions, pagination, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.docs.models.linkage import Linkage
from apps.docs.serializers.linkage_serializers import LinkageSerializer


class LinkagePagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500


class LinkageListCreateView(generics.ListCreateAPIView):
    queryset = Linkage.objects.all().order_by('-dt_modified')
    serializer_class = LinkageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LinkagePagination

    def get_queryset(self):
        qs = super().get_queryset()
        purpose = self.request.GET.get('purpose')
        if purpose:
            qs = qs.filter(purpose=purpose)
        return qs


class LinkageRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Linkage.objects.all()
    serializer_class = LinkageSerializer
    permission_classes = [permissions.IsAuthenticated]


class LinkageAddRemoveLinkView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        linkage = get_object_or_404(Linkage, pk=pk)
        table = request.data.get('table')
        record_id = request.data.get('record_id')
        if not table or record_id is None:
            return Response({'detail': 'table and record_id required'}, status=status.HTTP_400_BAD_REQUEST)
        added = linkage.add_link(table, record_id)
        if added:
            linkage.save()
        return Response({'added': added, 'link_counts': linkage.link_counts()})

    def delete(self, request, pk):
        linkage = get_object_or_404(Linkage, pk=pk)
        table = request.data.get('table') or request.GET.get('table')
        record_id = request.data.get('record_id') or request.GET.get('record_id')
        if not table or record_id is None:
            return Response({'detail': 'table and record_id required'}, status=status.HTTP_400_BAD_REQUEST)
        removed = linkage.remove_link(table, record_id)
        if removed:
            linkage.save()
        return Response({'removed': removed, 'link_counts': linkage.link_counts()})
