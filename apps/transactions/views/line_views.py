from decimal import Decimal, InvalidOperation
from django.db.models import Sum, F
from django.http import Http404
from rest_framework import generics, permissions, response, views, status, pagination
from apps.core.permissions import ViewEditPermission
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
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
    ProjectSerializer,
)
from rest_framework.views import APIView
from apps.core.permissions import get_role_field_rules
from apps.transactions.aggregation import compute_line_aggregate, DEFAULT_CACHE_TTL_SECONDS
from apps.transactions.models.projects import Project
from apps.core.constants.model_registry import get_model_meta, import_model

class BasePermission(ViewEditPermission):
    """Combines auth + view_edit rule enforcement (ViewEditPermission already checks auth)."""
    pass

# Parent (header) endpoints -------------------------------------------------
class DefaultPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500

class ProposalListCreate(generics.ListCreateAPIView):
    queryset = Proposal.objects.all().order_by('-id')
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class ProposalRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]

@extend_schema(
    summary="List/Create proposal lines",
    parameters=[OpenApiParameter(name='parent_id', description='Filter by parent_id', required=False, type=int)],
)
class ProposalLineListCreate(generics.ListCreateAPIView):
    queryset = ProposalLine.objects.all().order_by('-id')
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination

class ProposalLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalLine.objects.all()
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]

# SalesOrder
class SalesOrderListCreate(generics.ListCreateAPIView):
    queryset = SalesOrder.objects.all().order_by('-id')
    serializer_class = SalesOrderSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class SalesOrderRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create sales order lines")
class SalesOrderLineListCreate(generics.ListCreateAPIView):
    queryset = SalesOrderLine.objects.all().order_by('-id')
    serializer_class = SalesOrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination

class SalesOrderLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = SalesOrderLine.objects.all()
    serializer_class = SalesOrderLineSerializer
    permission_classes = [BasePermission]

# Invoice
class InvoiceListCreate(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class InvoiceRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create invoice lines")
class InvoiceLineListCreate(generics.ListCreateAPIView):
    queryset = InvoiceLine.objects.all().order_by('-id')
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination

class InvoiceLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceLine.objects.all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]

# PurchaseOrder
class PurchaseOrderListCreate(generics.ListCreateAPIView):
    queryset = PurchaseOrder.objects.all().order_by('-id')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class PurchaseOrderRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create purchase order lines")
class PurchaseOrderLineListCreate(generics.ListCreateAPIView):
    queryset = PurchaseOrderLine.objects.all().order_by('-id')
    serializer_class = PurchaseOrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination

class PurchaseOrderLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrderLine.objects.all()
    serializer_class = PurchaseOrderLineSerializer
    permission_classes = [BasePermission]

# WorkOrder
class WorkOrderListCreate(generics.ListCreateAPIView):
    queryset = WorkOrder.objects.all().order_by('-id')
    serializer_class = WorkOrderSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class WorkOrderRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create workorder lines")
class WorkOrderLineListCreate(generics.ListCreateAPIView):
    queryset = WorkOrderLine.objects.all().order_by('-id')
    serializer_class = WorkOrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination

class WorkOrderLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkOrderLine.objects.all()
    serializer_class = WorkOrderLineSerializer
    permission_classes = [BasePermission]

# Requisition
class RequisitionListCreate(generics.ListCreateAPIView):
    queryset = Requisition.objects.all().order_by('-id')
    serializer_class = RequisitionSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class RequisitionRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Requisition.objects.all()
    serializer_class = RequisitionSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create requisition lines")
class RequisitionLineListCreate(generics.ListCreateAPIView):
    queryset = RequisitionLine.objects.all().order_by('-id')
    serializer_class = RequisitionLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']
    pagination_class = DefaultPagination


@extend_schema(
    summary="Aggregate totals across line types for a parent (with optional model scope)",
    parameters=[
        OpenApiParameter(name='parent_id', description='Parent id', required=True, type=int),
    OpenApiParameter(name='model', description='Optional line model code to scope aggregation (e.g., proposal-line)', required=False, type=str,
              enum=['proposal-line','sales-order-line','invoice-line','purchase-order-line','workorder-line','requisition-line']),
        OpenApiParameter(name='ttl', description='Override cache TTL seconds (min 5). Default '+str(DEFAULT_CACHE_TTL_SECONDS), required=False, type=int),
        OpenApiParameter(name='include_breakdown', description='Include per-model breakdown even when scoped (0/1)', required=False, type=bool),
    ],
    responses={200: OpenApiResponse(description='Aggregation result (may include breakdown, ttl_seconds, cache_window)')}
)
class LineAggregateView(views.APIView):
    permission_classes = [BasePermission]
    throttle_scope = 'tx_aggregate'

    def get(self, request, *args, **kwargs):
        qp = request.query_params
        parent_id_val = qp.get('parent_id') or qp.get('parent_ref_id')
        if not parent_id_val:
            return response.Response({"detail": "parent_id required"}, status=status.HTTP_400_BAD_REQUEST)
        model_key = qp.get('model')
        ttl_param = qp.get('ttl')
        include_breakdown_param = qp.get('include_breakdown')
        try:
            parent_id_int = int(parent_id_val)
        except ValueError:
            return response.Response({'detail': 'parent_id invalid'}, status=400)
        ttl_override = None
        if ttl_param is not None:
            try:
                ttl_override = int(ttl_param)
            except ValueError:
                return response.Response({'detail': 'ttl invalid'}, status=400)
        include_breakdown = False
        if include_breakdown_param is not None:
            include_breakdown = include_breakdown_param in ('1','true','True','yes')
        try:
            result = compute_line_aggregate(parent_id_int, model_key, ttl_seconds=ttl_override, include_breakdown=include_breakdown)
        except ValueError:
            return response.Response({'detail': 'Invalid model parameter'}, status=400)
        return response.Response(result)


@extend_schema(
    summary="Return authorized view/edit fields for a model",
    parameters=[OpenApiParameter(
        name='model', description='Model code', required=True, type=str,
      enum=['proposal-line','sales-order-line','invoice-line','purchase-order-line','workorder-line','requisition-line',
          'proposal','sales-order','invoice','purchase-order','workorder','requisition']
    )],
    responses={200: OpenApiResponse(description='Role field permissions')}
)
class FieldAuthMatrixView(APIView):
    permission_classes = [BasePermission]
    throttle_scope = 'tx_parent'

    MODEL_MAP = {
        'proposal-line': ProposalLine,
    'sales-order-line': SalesOrderLine,
    'invoice-line': InvoiceLine,
    'purchase-order-line': PurchaseOrderLine,
        'workorder-line': WorkOrderLine,
        'requisition-line': RequisitionLine,
        'proposal': Proposal,
    'sales-order': SalesOrder,
    'invoice': Invoice,
    'purchase-order': PurchaseOrder,
        'workorder': WorkOrder,
        'requisition': Requisition,
    }

    def get(self, request, *args, **kwargs):
        model_key = request.query_params.get('model')
        if not model_key or model_key not in self.MODEL_MAP:
            return response.Response({'detail': 'Invalid or missing model parameter'}, status=400)
        model = self.MODEL_MAP[model_key]
        role = getattr(request.user, 'role', '')
        rules = get_role_field_rules(model, role)
        return response.Response({'model': model_key, 'role': role, 'rules': rules})


@extend_schema(
    summary="Batch authorized view/edit fields for multiple models",
    request=None,
    parameters=[OpenApiParameter(
        name='models', description='Comma separated model codes', required=True, type=str,
    )],
    responses={200: OpenApiResponse(description='Mapping of model -> rules')}
)
class FieldAuthMatrixBatchView(APIView):
    permission_classes = [BasePermission]
    throttle_scope = 'tx_parent'

    MODEL_MAP = FieldAuthMatrixView.MODEL_MAP

    def _build_response(self, model_keys, role):
        result = {}
        for key in model_keys:
            model = self.MODEL_MAP.get(key)
            if not model:
                result[key] = {'error': 'invalid-model'}
                continue
            result[key] = get_role_field_rules(model, role)
        return result

    def get(self, request, *args, **kwargs):
        models_param = request.query_params.get('models')
        if not models_param:
            return response.Response({'detail': 'models query parameter required'}, status=400)
        role = getattr(request.user, 'role', '')
        keys = [m.strip() for m in models_param.split(',') if m.strip()]
        data = self._build_response(keys, role)
        return response.Response({'role': role, 'models': data})

    @extend_schema(request={'application/json': {'type': 'object', 'properties': {'models': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['models']}},
                   responses={200: OpenApiResponse(description='Mapping of model -> rules')})
    def post(self, request, *args, **kwargs):
        body = request.data or {}
        models_list = body.get('models')
        if not isinstance(models_list, list) or not models_list:
            return response.Response({'detail': 'models array required'}, status=400)
        # dedupe while preserving order
        seen = set()
        keys = []
        for k in models_list:
            if isinstance(k, str) and k not in seen:
                seen.add(k)
                keys.append(k)
        role = getattr(request.user, 'role', '')
        data = self._build_response(keys, role)
        return response.Response({'role': role, 'models': data})

class RequisitionLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = RequisitionLine.objects.all()
    serializer_class = RequisitionLineSerializer
    permission_classes = [BasePermission]


# ---------------- Projects -------------------------------------------------
class ProjectListCreate(generics.ListCreateAPIView):
    queryset = Project.objects.all().order_by('-id')
    serializer_class = ProjectSerializer
    # Use plain IsAuthenticated to avoid needing dynamic view/edit settings for base project CRUD
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filterset_fields = ['status', 'priority', 'attention', 'category', 'contact_id']
    search_fields = ['situation', 'intent', 'objective']
    ordering_fields = ['id', 'priority', 'status', 'attention', 'burndown', 'profit', 'dt_modified']


class ProjectRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

# If you previously had dicts like:
# MODEL_BY_NAME = {'requisition-line': RequisitionLine, 'requisition': Requisition, ...}
# Replace with a resolver function:
def resolve_model(token: str):
    cls = import_model(token)
    if cls is None:
        raise Http404(f'Unknown model: {token}')
    return cls

# Example usage where a model name comes from a query param/path:
# model_token = self.request.query_params.get('model') or self.kwargs.get('model')
# model_cls = resolve_model(model_token)
# queryset = model_cls.objects.all()
