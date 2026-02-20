from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.base_views import BaseOptimisticDetailView
from apps.transactions.models import (
    Proposal, Order, Purchase, Invoice, Payment
)
from apps.transactions.serializers import (
    ProposalSerializer, OrderSerializer, PurchaseSerializer,
    InvoiceSerializer, PaymentSerializer
)
from apps.transactions.services import proposal_to_order, order_to_invoice, inventory_flow
from apps.transactions.services.flow import receive_purchase, ReceiveLine


class ProposalViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Proposal. Writes go through /wcapi/save/."""

    queryset = Proposal.objects.active().prefetch_related('lines')
    serializer_class = ProposalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer', 'vendor']

    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convert proposal to order."""
        proposal = self.get_object()
        try:
            result = proposal_to_order.transfer_proposal_to_order(
                proposal=proposal,
                line_ids=request.data.get('line_ids'),
                transfer_all=request.data.get('transfer_all', True),
                order_status=request.data.get('order_status', 'confirmed'),
                preserve_proposal=request.data.get('preserve_proposal', True),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Order. Writes go through /wcapi/save/."""

    queryset = Order.objects.active().prefetch_related('lines')
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer', 'vendor', 'ida']

    @action(detail=True, methods=['post'])
    def convert_to_invoice(self, request, pk=None):
        """Convert order to invoice."""
        order = self.get_object()
        try:
            result = order_to_invoice.transfer_order_to_invoice(
                order=order,
                line_ids=request.data.get('line_ids'),
                transfer_all=request.data.get('transfer_all', True),
                invoice_status=request.data.get('invoice_status', 'pending'),
                preserve_order=request.data.get('preserve_order', True),
                invoice_type=request.data.get('invoice_type', 'standard'),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_purchase(self, request, pk=None):
        """Create purchase from order."""
        from apps.transactions.services.order_to_purchase import transfer_order_to_purchase

        order = self.get_object()
        group_by_vendor = request.data.get('group_by_vendor', True)
        line_ids = request.data.get('line_ids')

        try:
            result = transfer_order_to_purchase(
                order=order,
                line_ids=line_ids,
                transfer_all=line_ids is None,
                group_by_vendor=group_by_vendor
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reserve_inventory(self, request, pk=None):
        """Reserve inventory for order."""
        order = self.get_object()
        try:
            result = inventory_flow.reserve_inventory_for_order(order)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Purchase. Writes go through /wcapi/save/."""

    queryset = Purchase.objects.active().prefetch_related('lines')
    serializer_class = PurchaseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer', 'vendor', 'ida']

    @action(detail=True, methods=['post'])
    def receive_goods(self, request, pk=None):
        """Record receipt of goods."""
        purchase = self.get_object()
        receipt_id = request.data.get('receipt_id')
        if not receipt_id:
            return Response({'error': 'receipt_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        lines_data = request.data.get('lines', [])
        if not lines_data:
            return Response({'error': 'lines are required'}, status=status.HTTP_400_BAD_REQUEST)

        lines = []
        for ld in lines_data:
            lines.append(ReceiveLine(
                po_line_id=ld.get('po_line_id') or ld['purchase_line_id'],
                qty=ld['qty'],
                warehouse_code=ld['warehouse_code'],
                unit_cost=ld.get('unit_cost'),
                lot=ld.get('lot'),
                serial_batch=ld.get('serial_batch')
            ))

        try:
            result = receive_purchase(purchase, receipt_id, lines)
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def totals(self, request, pk=None):
        """Get detailed totals for purchase."""
        purchase = self.get_object()
        totals = purchase.update_sell_cost_totals(persist=False)
        return Response(totals)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Invoice. Writes go through /wcapi/save/."""

    queryset = Invoice.objects.active()
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer', 'vendor']

    @action(detail=True, methods=['get'])
    def payment_status(self, request, pk=None):
        """Get payment status for invoice."""
        invoice = self.get_object()
        return Response({'message': 'Payment status endpoint - implementation needed'})


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Payment. Writes go through /wcapi/save/."""

    queryset = Payment.objects.active()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'gateway', 'contact', 'invoice', 'payment_method']


__all__ = [
    'ProposalViewSet',
    'OrderViewSet',
    'PurchaseViewSet',
    'InvoiceViewSet',
    'PaymentViewSet',
]