from typing import Tuple, Type, Optional
from django.shortcuts import get_object_or_404
from rest_framework import generics
from apps.transactions.models.line_variants import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    Workorder, WorkorderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.serializers.line_serializers import (
    ProposalSerializer, ProposalLineSerializer,
    OrderSerializer, OrderLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer,
    PurchaseSerializer, PurchaseLineSerializer,
    WorkorderSerializer, WorkorderLineSerializer,
    RequisitionSerializer, RequisitionLineSerializer,
)
from apps.transactions.views.line_views import BasePermission, DefaultPagination


# Mapping helpers -----------------------------------------------------------
HEADER_MAP = {
    'proposal': (Proposal, ProposalSerializer, ProposalLine, ProposalLineSerializer),
    'order': (Order, OrderSerializer, OrderLine, OrderLineSerializer),
    'invoice': (Invoice, InvoiceSerializer, InvoiceLine, InvoiceLineSerializer),
    'purchase': (Purchase, PurchaseSerializer, PurchaseLine, PurchaseLineSerializer),
    'workorder': (Workorder, WorkorderSerializer, WorkorderLine, WorkorderLineSerializer),
    'requisition': (Requisition, RequisitionSerializer, RequisitionLine, RequisitionLineSerializer),
}


class _KindMixin:
    """Extracts kind from URL kwargs and exposes model + serializer accessors."""
    kind: Optional[str] = None

    def _resolve(self) -> Tuple[Type, Type, Type, Type]:
        kind = self.kind or ''
        mapping = HEADER_MAP.get(kind)
        if not mapping:
            raise ValueError(f"Unsupported transaction kind '{kind}'")
        return mapping  # header_model, header_serializer, line_model, line_serializer

    def get_header_model(self):
        return self._resolve()[0]

    def get_header_serializer(self):
        return self._resolve()[1]

    def get_line_model(self):
        return self._resolve()[2]

    def get_line_serializer(self):
        return self._resolve()[3]

    def initialize_kind(self, **kwargs):  # called from dispatch in subclasses
        k = kwargs.get('kind')
        if isinstance(k, str):
            self.kind = k


class TransactionHeaderListCreate(_KindMixin, generics.ListCreateAPIView):
    """Unified list/create endpoint for any transaction header kind.

    GET /api/tx/<kind>/  (paginated list)
    POST /api/tx/<kind>/ { ...fields... }
    """
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        Model = self.get_header_model()
        return Model.objects.all().order_by('-id')

    def get_serializer_class(self):
        return self.get_header_serializer()


class TransactionHeaderDetail(_KindMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve/Update/Delete for a header kind."""
    permission_classes = [BasePermission]

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_header_model().objects.all()

    def get_serializer_class(self):
        return self.get_header_serializer()


class TransactionLineListCreate(_KindMixin, generics.ListCreateAPIView):
    """List/Create lines nested under a header.

    GET /api/tx/<kind>/<id>/lines/
    POST /api/tx/<kind>/<id>/lines/ {...fields except parent...}
    """
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        LineModel = self.get_line_model()
        return LineModel.objects.filter(parent_id=self.header_id).order_by('-id')

    def get_serializer_class(self):
        return self.get_line_serializer()

    def perform_create(self, serializer):
        HeaderModel = self.get_header_model()
        parent = get_object_or_404(HeaderModel, pk=self.header_id)
        serializer.save(parent=parent)


class TransactionLineDetail(_KindMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve/Update/Delete a specific line within a header.

    GET /api/tx/<kind>/<id>/lines/<line_pk>/
    """
    permission_classes = [BasePermission]
    lookup_url_kwarg = 'line_pk'

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        LineModel = self.get_line_model()
        # Ensure line belongs to the header id context
        return LineModel.objects.filter(parent_id=self.header_id)

    def get_serializer_class(self):
        return self.get_line_serializer()

    def update(self, request, *args, **kwargs):  # ensure parent immutability via path
        # Strip parent if provided to prevent reassignment
        if isinstance(request.data, dict) and 'parent' in request.data:
            mutable_data = request.data.copy()
            mutable_data.pop('parent', None)
            request._full_data = mutable_data  # type: ignore
        return super().update(request, *args, **kwargs)


# Lightweight kind discovery endpoint (optional future): could list supported kinds.
