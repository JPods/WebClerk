from __future__ import annotations

from typing import Any, Dict, List

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import pagination

from apps.core.constants.model_registry import get_model_meta
from apps.docs.models.linkage import Linkage
from apps.docs.models.linkage_index import LinkageIndex
from apps.docs.serializers.document_serializers import DocumentSerializer
from apps.core.models.action import Action
from apps.core.serializers.action import ActionSerializer


class _StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def _get_linkage_for_model_record(model: str, pk: int) -> Linkage | None:
    meta = get_model_meta(model)
    if not meta:
        return None
    table = meta.import_model()._meta.db_table  # type: ignore[attr-defined]
    idx = LinkageIndex.objects.filter(table_name=table, record_id=pk).first()
    if not idx:
        return None
    return idx.linkage


class RelatedDocumentsView(APIView):
    pagination_class = _StandardPagination

    def get(self, request, *args, **kwargs):
        model = str(kwargs.get('model') or '')
        pk = int(kwargs.get('pk') or 0)
        linkage = _get_linkage_for_model_record(model, pk)
        if not linkage:
            return Response({'count': 0, 'results': []})
        # Gather document ids from linkage refs.links if present
        refs = getattr(linkage, 'refs', {}) or {}
        links = refs.get('links') if isinstance(refs, dict) else {}
        doc_ids: List[int] = []
        if isinstance(links, dict):
            doc_ids = links.get('documents') or links.get('documents_document') or []  # support legacy keys if any
        from apps.docs.models.document import Document
        qs = Document.objects.filter(id__in=doc_ids).order_by('-dt_modified') if doc_ids else Document.objects.none()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        ser = DocumentSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)


class RelatedActionsView(APIView):
    pagination_class = _StandardPagination

    def get(self, request, *args, **kwargs):
        model = str(kwargs.get('model') or '')
        pk = int(kwargs.get('pk') or 0)
        linkage = _get_linkage_for_model_record(model, pk)
        if not linkage:
            return Response({'count': 0, 'results': []})
        # Find actions that link to this model record id or linkage id
        # Prefer linkage based association: actions.refs.links.linkage contains linkage.id
        from django.db.models import Q
        # We match actions that are linked by linkage id or directly by table name bucket
        meta = get_model_meta(model)
        table = meta.import_model()._meta.db_table if meta else model
        q = Q(refs__links__linkage__contains=[linkage.id]) | Q(refs__links__contains={table: [pk]})
        qs = Action.objects.filter(q).order_by('-dt_modified')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        ser = ActionSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)
