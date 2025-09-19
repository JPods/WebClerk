from typing import Tuple, Type, Optional
from django.shortcuts import get_object_or_404
from rest_framework import generics, response, status
from common.api_responses import api_response
from apps.transactions.models import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
    WorkOrder, WorkOrderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.serializers.line_serializers import (
    ProposalSerializer, ProposalLineSerializer,
    SalesOrderSerializer, SalesOrderLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer,
    PurchaseOrderSerializer, PurchaseOrderLineSerializer,
    WorkOrderSerializer, WorkOrderLineSerializer,
    RequisitionSerializer, RequisitionLineSerializer,
)
from apps.transactions.views.line_views import BasePermission, DefaultPagination
from apps.transactions.aggregation import compute_line_aggregate
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse


# Mapping helpers -----------------------------------------------------------
HEADER_MAP = {
    'proposal': (Proposal, ProposalSerializer, ProposalLine, ProposalLineSerializer),
    'sales-order': (SalesOrder, SalesOrderSerializer, SalesOrderLine, SalesOrderLineSerializer),
    'invoice': (Invoice, InvoiceSerializer, InvoiceLine, InvoiceLineSerializer),
    'purchase-order': (PurchaseOrder, PurchaseOrderSerializer, PurchaseOrderLine, PurchaseOrderLineSerializer),
    'workorder': (WorkOrder, WorkOrderSerializer, WorkOrderLine, WorkOrderLineSerializer),
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


@extend_schema(
    summary="Preview totals for a header",
    parameters=[OpenApiParameter(name='include_breakdown', required=False, type=bool, description='Include per-model breakdown (0/1)')],
    responses={200: OpenApiResponse(description='Aggregate totals payload in unified envelope')}
)
class TransactionTotalsPreview(_KindMixin, generics.GenericAPIView):
    """Read-only totals preview for a header using line aggregation.

    GET /api/tx/<kind>/<id>/preview-totals/?include_breakdown=1
    """
    permission_classes = [BasePermission]

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    # Provide queryset so ViewEditPermission can resolve model for permission rules
    def get_queryset(self):
        return self.get_header_model().objects.all()

    def get(self, request, *args, **kwargs):  # noqa: D401
        """Return aggregate totals for this header's lines.

        By default, scopes aggregation to this kind's line model (e.g., sales-order-line).
        Pass include_breakdown=1 to include per-model breakdown (useful if future variants
        also link to the same header id).
        """
        # Validate header id
        if self.header_id is None:
            return response.Response({'detail': 'Missing header id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            header_id = int(self.header_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return response.Response({'detail': 'Invalid header id'}, status=status.HTTP_400_BAD_REQUEST)

        include_breakdown_param = request.query_params.get('include_breakdown')
        include_breakdown = include_breakdown_param in ('1', 'true', 'True', 'yes')
        kind = self.kind or ''
        model_key = f"{kind}-line" if kind else None
        try:
            data = compute_line_aggregate(header_id, model_key, include_breakdown=include_breakdown)
        except ValueError:
            return response.Response({'detail': 'Invalid kind'}, status=status.HTTP_400_BAD_REQUEST)
        return api_response(data=data)
