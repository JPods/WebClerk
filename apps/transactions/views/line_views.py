from decimal import Decimal, InvalidOperation
from django.db.models import Sum, F
from django.http import Http404
from django.apps import apps
from rest_framework.response import Response  # added
from rest_framework import status  # added
from rest_framework import generics, permissions, views, pagination, response

from apps.core.permissions import ViewEditPermission
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.serializers.line_serializers import (
    ProposalSerializer, ProposalLineSerializer,
    OrderSerializer, OrderLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer,
    PurchaseSerializer, PurchaseLineSerializer,
    WorkOrderSerializer, WorkOrderLineSerializer,
    RequisitionSerializer, RequisitionLineSerializer,
    ProjectSerializer,
)
from rest_framework.views import APIView
from apps.core.permissions import get_role_field_rules
from apps.transactions.aggregation import compute_line_aggregate, DEFAULT_CACHE_TTL_SECONDS
from apps.transactions.models.projects import Project
from apps.core.constants.model_registry import get_model_meta, import_model
from apps.transactions.pagination import TransactionPagination
from apps.transactions.response_envelope import EnvelopeResponseMixin, ListResponseEnvelopeMixin

class BasePermission(ViewEditPermission):
    """Combines auth + view_edit rule enforcement (ViewEditPermission already checks auth)."""
    pass

# Parent (header) endpoints -------------------------------------------------
class DefaultPagination(TransactionPagination):
    """Standard pagination with metadata envelope for transaction endpoints."""
    pass

class ProposalListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Proposal.objects.active().order_by('-id')
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class ProposalRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Proposal.objects.active()
    serializer_class = ProposalSerializer
    permission_classes = [BasePermission]

@extend_schema(
    summary="List/Create proposal lines",
    parameters=[OpenApiParameter(name='parent_id', description='Filter by parent_id', required=False, type=int)],
)
class ProposalLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = ProposalLine.objects.active().order_by('-id')
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['proposal', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'proposal', 'status']
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        """Create line via LineItemService for inventory tracking (on_p forecast)."""
        from apps.transactions.services.line_item_service import LineItemService
        
        instance = serializer.save()
        instance._pending_created = True
        
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=instance.proposal,
            parent_model_key='proposal',
            line=instance,
            line_data=serializer.validated_data,
        )


class ProposalLineRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalLine.objects.active()
    serializer_class = ProposalLineSerializer
    permission_classes = [BasePermission]

    def perform_update(self, serializer):
        """Update line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        old_instance = self.get_object()
        old_qty = float((old_instance.quantity or {}).get('placed', 0) or 0)
        old_item_id = (old_instance.item or {}).get('item_id') or (old_instance.item or {}).get('id')
        
        instance = serializer.save()
        
        new_qty = float((instance.quantity or {}).get('placed', 0) or 0)
        new_item_id = (instance.item or {}).get('item_id') or (instance.item or {}).get('id')
        
        service = LineItemService(create_pending=True)
        
        if old_item_id and new_item_id and old_item_id != new_item_id:
            if old_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.proposal,
                    transaction_type='proposal',
                    line=instance,
                    quantity_released=old_qty,
                )
            if new_qty > 0:
                instance._pending_created = True
                service._create_pending_for_new_line(
                    parent=instance.proposal,
                    parent_model_key='proposal',
                    line=instance,
                    line_data=serializer.validated_data,
                )
        else:
            qty_delta = new_qty - old_qty
            if qty_delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.proposal,
                    transaction_type='proposal',
                    line=instance,
                    quantity_delta=qty_delta,
                )

    def perform_destroy(self, instance):
        """Delete line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        qty_to_release = float((instance.quantity or {}).get('placed', 0) or 0)
        
        if qty_to_release > 0:
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=instance.proposal,
                transaction_type='proposal',
                line=instance,
                quantity_released=qty_to_release,
            )
        
        instance.delete()

# Order
class OrderListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Order.objects.active().order_by('-id')
    serializer_class = OrderSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class OrderRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.active()
    serializer_class = OrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create order lines")
class OrderLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = OrderLine.objects.active().order_by('-id')
    serializer_class = OrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['order', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'order', 'status']
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        """Create line via LineItemService for inventory tracking (on_so reservation)."""
        from apps.transactions.services.line_item_service import LineItemService
        
        instance = serializer.save()
        instance._pending_created = True
        
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=instance.order,
            parent_model_key='order',
            line=instance,
            line_data=serializer.validated_data,
        )


class OrderLineRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderLine.objects.active()
    serializer_class = OrderLineSerializer
    permission_classes = [BasePermission]

    def perform_update(self, serializer):
        """Update line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        old_instance = self.get_object()
        old_qty = float((old_instance.quantity or {}).get('placed', 0) or 0)
        old_item_id = (old_instance.item or {}).get('item_id') or (old_instance.item or {}).get('id')
        
        instance = serializer.save()
        
        new_qty = float((instance.quantity or {}).get('placed', 0) or 0)
        new_item_id = (instance.item or {}).get('item_id') or (instance.item or {}).get('id')
        
        service = LineItemService(create_pending=True)
        
        if old_item_id and new_item_id and old_item_id != new_item_id:
            if old_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.order,
                    transaction_type='order',
                    line=instance,
                    quantity_released=old_qty,
                )
            if new_qty > 0:
                instance._pending_created = True
                service._create_pending_for_new_line(
                    parent=instance.order,
                    parent_model_key='order',
                    line=instance,
                    line_data=serializer.validated_data,
                )
        else:
            qty_delta = new_qty - old_qty
            if qty_delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.order,
                    transaction_type='order',
                    line=instance,
                    quantity_delta=qty_delta,
                )

    def perform_destroy(self, instance):
        """Delete line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        qty_to_release = float((instance.quantity or {}).get('placed', 0) or 0)
        
        if qty_to_release > 0:
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=instance.order,
                transaction_type='order',
                line=instance,
                quantity_released=qty_to_release,
            )
        
        instance.delete()

# Invoice
class InvoiceListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Invoice.objects.active().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class InvoiceRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.active()
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create invoice lines")
class InvoiceLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = InvoiceLine.objects.active().order_by('-id')
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['invoice', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'invoice', 'status']
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        """Create line via LineItemService for inventory tracking (on_in issuance)."""
        from apps.transactions.services.line_item_service import LineItemService
        
        instance = serializer.save()
        instance._pending_created = True
        
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=instance.invoice,
            parent_model_key='invoice',
            line=instance,
            line_data=serializer.validated_data,
        )


class InvoiceLineRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceLine.objects.active()
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]

    def perform_update(self, serializer):
        """Update line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        old_instance = self.get_object()
        old_qty = float((old_instance.quantity or {}).get('placed', 0) or 0)
        old_item_id = (old_instance.item or {}).get('item_id') or (old_instance.item or {}).get('id')
        
        instance = serializer.save()
        
        new_qty = float((instance.quantity or {}).get('placed', 0) or 0)
        new_item_id = (instance.item or {}).get('item_id') or (instance.item or {}).get('id')
        
        service = LineItemService(create_pending=True)
        
        if old_item_id and new_item_id and old_item_id != new_item_id:
            if old_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.invoice,
                    transaction_type='invoice',
                    line=instance,
                    quantity_released=old_qty,
                )
            if new_qty > 0:
                instance._pending_created = True
                service._create_pending_for_new_line(
                    parent=instance.invoice,
                    parent_model_key='invoice',
                    line=instance,
                    line_data=serializer.validated_data,
                )
        else:
            qty_delta = new_qty - old_qty
            if qty_delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.invoice,
                    transaction_type='invoice',
                    line=instance,
                    quantity_delta=qty_delta,
                )

    def perform_destroy(self, instance):
        """Delete line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        qty_to_release = float((instance.quantity or {}).get('placed', 0) or 0)
        
        if qty_to_release > 0:
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=instance.invoice,
                transaction_type='invoice',
                line=instance,
                quantity_released=qty_to_release,
            )
        
        instance.delete()

# Purchase
class PurchaseListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Purchase.objects.active().order_by('-id')
    serializer_class = PurchaseSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class PurchaseRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Purchase.objects.active()
    serializer_class = PurchaseSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create purchase order lines")
class PurchaseLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = PurchaseLine.objects.active().order_by('-id')
    serializer_class = PurchaseLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['purchase', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'purchase', 'status']
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        """Create line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        instance = serializer.save()
        # Mark as pending handled to prevent signal duplicates
        instance._pending_created = True
        
        # Create pending inventory via LineItemService
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=instance.purchase,
            parent_model_key='purchase',
            line=instance,
            line_data=serializer.validated_data,
        )


class PurchaseLineRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseLine.objects.active()
    serializer_class = PurchaseLineSerializer
    permission_classes = [BasePermission]

    def perform_update(self, serializer):
        """Update line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        # Get old quantity before update for delta calculation
        old_instance = self.get_object()
        old_qty = 0
        if isinstance(old_instance.quantity, dict):
            old_qty = float(old_instance.quantity.get('placed', 0) or 0)
        old_item_id = None
        if isinstance(old_instance.item, dict):
            old_item_id = old_instance.item.get('item_id') or old_instance.item.get('id')
        
        instance = serializer.save()
        
        # Get new quantity after update
        new_qty = 0
        if isinstance(instance.quantity, dict):
            new_qty = float(instance.quantity.get('placed', 0) or 0)
        new_item_id = None
        if isinstance(instance.item, dict):
            new_item_id = instance.item.get('item_id') or instance.item.get('id')
        
        # Create pending for quantity change via LineItemService
        service = LineItemService(create_pending=True)
        
        # If item changed, handle as delete of old + add of new
        if old_item_id and new_item_id and old_item_id != new_item_id:
            # Reverse old item
            if old_qty > 0 and old_item_id:
                service._create_pending_for_line_delete(
                    transaction=instance.purchase,
                    transaction_type='purchase',
                    line=instance,
                    quantity_released=old_qty,
                )
            # Add new item
            if new_qty > 0 and new_item_id:
                instance._pending_created = True
                service._create_pending_for_new_line(
                    parent=instance.purchase,
                    parent_model_key='purchase',
                    line=instance,
                    line_data=serializer.validated_data,
                )
        else:
            # Same item - handle quantity delta
            qty_delta = new_qty - old_qty
            if qty_delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.purchase,
                    transaction_type='purchase',
                    line=instance,
                    quantity_delta=qty_delta,
                )

    def perform_destroy(self, instance):
        """Delete line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        # Get quantity to release
        qty_to_release = 0
        if isinstance(instance.quantity, dict):
            qty_to_release = float(instance.quantity.get('placed', 0) or 0)
        
        # Create pending for delete before destroying
        if qty_to_release > 0:
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=instance.purchase,
                transaction_type='purchase',
                line=instance,
                quantity_released=qty_to_release,
            )
        
        instance.delete()

# WorkOrder
class WorkOrderListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = WorkOrder.objects.active().order_by('-id')
    serializer_class = WorkOrderSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class WorkOrderRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkOrder.objects.active()
    serializer_class = WorkOrderSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create workorder lines")
class WorkOrderLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = WorkOrderLine.objects.active().order_by('-id')
    serializer_class = WorkOrderLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['workorder', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'workorder', 'status']
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        """Create line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        instance = serializer.save()
        # Mark as pending handled to prevent signal duplicates
        instance._pending_created = True
        
        # Create pending inventory via LineItemService
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=instance.workorder,
            parent_model_key='workorder',
            line=instance,
            line_data=serializer.validated_data,
        )


class WorkOrderLineRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkOrderLine.objects.active()
    serializer_class = WorkOrderLineSerializer
    permission_classes = [BasePermission]

    def perform_update(self, serializer):
        """Update line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        # Get old quantity before update for delta calculation
        old_instance = self.get_object()
        old_qty = 0
        if isinstance(old_instance.quantity, dict):
            old_qty = float(old_instance.quantity.get('placed', 0) or 0)
        old_item_id = None
        if isinstance(old_instance.item, dict):
            old_item_id = old_instance.item.get('item_id') or old_instance.item.get('id')
        
        instance = serializer.save()
        
        # Get new quantity after update
        new_qty = 0
        if isinstance(instance.quantity, dict):
            new_qty = float(instance.quantity.get('placed', 0) or 0)
        new_item_id = None
        if isinstance(instance.item, dict):
            new_item_id = instance.item.get('item_id') or instance.item.get('id')
        
        # Create pending for quantity change via LineItemService
        service = LineItemService(create_pending=True)
        
        # If item changed, handle as delete of old + add of new
        if old_item_id and new_item_id and old_item_id != new_item_id:
            # Reverse old item
            if old_qty > 0 and old_item_id:
                service._create_pending_for_line_delete(
                    transaction=instance.workorder,
                    transaction_type='workorder',
                    line=instance,
                    quantity_released=old_qty,
                )
            # Add new item
            if new_qty > 0 and new_item_id:
                instance._pending_created = True
                service._create_pending_for_new_line(
                    parent=instance.workorder,
                    parent_model_key='workorder',
                    line=instance,
                    line_data=serializer.validated_data,
                )
        else:
            # Same item - handle quantity delta
            qty_delta = new_qty - old_qty
            if qty_delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.workorder,
                    transaction_type='workorder',
                    line=instance,
                    quantity_delta=qty_delta,
                )

    def perform_destroy(self, instance):
        """Delete line via LineItemService for inventory tracking."""
        from apps.transactions.services.line_item_service import LineItemService
        
        # Get quantity to release
        qty_to_release = 0
        if isinstance(instance.quantity, dict):
            qty_to_release = float(instance.quantity.get('placed', 0) or 0)
        
        # Create pending for delete before destroying
        if qty_to_release > 0:
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=instance.workorder,
                transaction_type='workorder',
                line=instance,
                quantity_released=qty_to_release,
            )
        
        instance.delete()

# Requisition
class RequisitionListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Requisition.objects.active().order_by('-id')
    serializer_class = RequisitionSerializer
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

class RequisitionRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Requisition.objects.active()
    serializer_class = RequisitionSerializer
    permission_classes = [BasePermission]

@extend_schema(summary="List/Create requisition lines")
class RequisitionLineListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = RequisitionLine.objects.active().order_by('-id')
    serializer_class = RequisitionLineSerializer
    permission_classes = [BasePermission]
    throttle_scope = 'tx_line'
    filterset_fields = ['requisition', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'requisition', 'status']
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
        'order-line': OrderLine,
        'invoice-line': InvoiceLine,
        'purchase-line': PurchaseLine,
        'workorder-line': WorkOrderLine,
        'requisition-line': RequisitionLine,
        'proposal': Proposal,
        'order': Order,
        'invoice': Invoice,
        'purchase': Purchase,
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
    queryset = RequisitionLine.objects.active()
    serializer_class = RequisitionLineSerializer
    permission_classes = [BasePermission]


# ---------------- Projects -------------------------------------------------
class ProjectListCreate(EnvelopeResponseMixin, ListResponseEnvelopeMixin, generics.ListCreateAPIView):
    queryset = Project.objects.active().order_by('-id')
    serializer_class = ProjectSerializer
    # Use plain IsAuthenticated to avoid needing dynamic view/edit settings for base project CRUD
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filterset_fields = ['status', 'priority', 'attention', 'category', 'id_contact']
    search_fields = ['situation', 'intent', 'objective']
    ordering_fields = ['id', 'priority', 'status', 'attention', 'burndown', 'profit', 'dt_modified']
    # Ensure POST allowed on list endpoint
    http_method_names = ["get", "post", "options", "head"]

    def post(self, request, *args, **kwargs):
        """
        Create a Project from provided JSON and return new id.
        Accepts keys: situation, objective, priority, status, attention, intent, category.
        """
        Project = apps.get_model("transactions", "Project")
        data = request.data or {}
        allowed = ["situation", "objective", "priority", "status", "attention", "intent", "category"]
        create_kwargs = {k: data.get(k) for k in allowed if data.get(k) is not None}
        obj = Project.objects.create(**create_kwargs)
        return Response({"id": obj.id}, status=status.HTTP_201_CREATED)

class ProjectRetrieveUpdate(EnvelopeResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.active()
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
# queryset = model_cls.objects.active()
