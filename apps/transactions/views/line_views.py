from decimal import Decimal, InvalidOperation
from django.db.models import Sum, F
from rest_framework import generics, permissions, response, views, status
from apps.core.permissions import ViewEditPermission
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
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
from rest_framework.views import APIView
from apps.core.permissions import get_role_field_rules
from apps.transactions.aggregation import compute_line_aggregate, DEFAULT_CACHE_TTL_SECONDS

class BasePermission(ViewEditPermission):
    """Combines auth + view_edit rule enforcement (ViewEditPermission already checks auth)."""
    pass

# Parent (header) endpoints -------------------------------------------------
class ProposalListCreate(generics.ListCreateAPIView):
    queryset = Proposal.objects.all().order_by('-id')
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]

class ProposalRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]

@extend_schema(
    summary="List/Create proposal lines",
    parameters=[OpenApiParameter(name='parent_ref_id', description='Filter by parent_ref_id', required=False, type=int)],
)
class ProposalLineListCreate(generics.ListCreateAPIView):
    queryset = ProposalLine.objects.all().order_by('-id')
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']

class ProposalLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalLine.objects.all()
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]

# Order
class OrderListCreate(generics.ListCreateAPIView):
    queryset = Order.objects.all().order_by('-id')
    serializer_class = OrderSerializer
    permission_classes = [BasePermission]

class OrderRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create order lines")
class OrderLineListCreate(generics.ListCreateAPIView):
    queryset = OrderLine.objects.all().order_by('-id')
    serializer_class = OrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']

class OrderLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderLine.objects.all()
    serializer_class = OrderLineSerializer
    permission_classes = [BasePermission]

# Invoice
class InvoiceListCreate(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]

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
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']

class InvoiceLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceLine.objects.all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]

# Purchase
class PurchaseListCreate(generics.ListCreateAPIView):
    queryset = Purchase.objects.all().order_by('-id')
    serializer_class = PurchaseSerializer
    permission_classes = [BasePermission]

class PurchaseRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create purchase lines")
class PurchaseLineListCreate(generics.ListCreateAPIView):
    queryset = PurchaseLine.objects.all().order_by('-id')
    serializer_class = PurchaseLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']

class PurchaseLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseLine.objects.all()
    serializer_class = PurchaseLineSerializer
    permission_classes = [BasePermission]

# Workorder
class WorkorderListCreate(generics.ListCreateAPIView):
    queryset = Workorder.objects.all().order_by('-id')
    serializer_class = WorkorderSerializer
    permission_classes = [BasePermission]

class WorkorderRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Workorder.objects.all()
    serializer_class = WorkorderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create workorder lines")
class WorkorderLineListCreate(generics.ListCreateAPIView):
    queryset = WorkorderLine.objects.all().order_by('-id')
    serializer_class = WorkorderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']

class WorkorderLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkorderLine.objects.all()
    serializer_class = WorkorderLineSerializer
    permission_classes = [BasePermission]

# Requisition
class RequisitionListCreate(generics.ListCreateAPIView):
    queryset = Requisition.objects.all().order_by('-id')
    serializer_class = RequisitionSerializer
    permission_classes = [BasePermission]

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
    filterset_fields = ['parent_ref_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_ref_id', 'status']


@extend_schema(
    summary="Aggregate totals across line types for a parent (with optional model scope)",
    parameters=[
        OpenApiParameter(name='parent_ref_id', description='Parent reference id', required=True, type=int),
        OpenApiParameter(name='model', description='Optional line model code to scope aggregation (e.g., proposal-line)', required=False, type=str,
                          enum=['proposal-line','order-line','invoice-line','purchase-line','workorder-line','requisition-line']),
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
        parent_ref_id = qp.get('parent_ref_id')
        if not parent_ref_id:
            return response.Response({"detail": "parent_ref_id required"}, status=status.HTTP_400_BAD_REQUEST)
        model_key = qp.get('model')
        ttl_param = qp.get('ttl')
        include_breakdown_param = qp.get('include_breakdown')
        try:
            parent_ref_id_int = int(parent_ref_id)
        except ValueError:
            return response.Response({'detail': 'parent_ref_id invalid'}, status=400)
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
            result = compute_line_aggregate(parent_ref_id_int, model_key, ttl_seconds=ttl_override, include_breakdown=include_breakdown)
        except ValueError:
            return response.Response({'detail': 'Invalid model parameter'}, status=400)
        return response.Response(result)


@extend_schema(
    summary="Return authorized view/edit fields for a model",
    parameters=[OpenApiParameter(
        name='model', description='Model code', required=True, type=str,
        enum=['proposal-line','order-line','invoice-line','purchase-line','workorder-line','requisition-line',
              'proposal','order','invoice','purchase','workorder','requisition']
    )],
    responses={200: OpenApiResponse(description='Role field permissions')}
)
class FieldAuthMatrixView(APIView):
    permission_classes = [BasePermission]
    throttle_scope = 'tx_parent'

    MODEL_MAP = {
        'proposal-line': ProposalLine,
        'order-line': OrderLine,
        'invoice-line': InvoiceLine,
        'purchase-line': PurchaseLine,
        'workorder-line': WorkorderLine,
        'requisition-line': RequisitionLine,
        'proposal': Proposal,
        'order': Order,
        'invoice': Invoice,
        'purchase': Purchase,
        'workorder': Workorder,
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
