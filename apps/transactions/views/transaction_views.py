from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.base_views import BaseOptimisticDetailView
from apps.transactions.models import (
    Proposal, SalesOrder, PurchaseOrder, Invoice, Payment
)
from apps.transactions.serializers import (
    ProposalSerializer, SalesOrderSerializer, PurchaseOrderSerializer,
    InvoiceSerializer, PaymentSerializer
)


class ProposalViewSet(viewsets.ModelViewSet):
    """ViewSet for Proposal transactions."""

    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer_id', 'vendor_id']

    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convert proposal to sales order."""
        proposal = self.get_object()
        # Implementation would call transfer service
        return Response({'message': 'Conversion endpoint - implementation needed'})


class SalesOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Sales Order transactions."""

    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer_id', 'vendor_id', 'order_no']

    @action(detail=True, methods=['post'])
    def convert_to_invoice(self, request, pk=None):
        """Convert order to invoice."""
        order = self.get_object()
        return Response({'message': 'Conversion endpoint - implementation needed'})

    @action(detail=True, methods=['post'])
    def create_purchase_order(self, request, pk=None):
        """Create purchase order from sales order."""
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
        return Response({'message': 'Inventory reservation endpoint - implementation needed'})


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order transactions."""

    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer_id', 'vendor_id', 'po_no']

    @action(detail=True, methods=['post'])
    def receive_goods(self, request, pk=None):
        """Record receipt of goods."""
        from apps.transactions.services.flow import receive_purchase_order, ReceiveLine

        po = self.get_object()
        receipt_no = request.data.get('receipt_no')
        if not receipt_no:
            return Response({'error': 'receipt_no is required'}, status=status.HTTP_400_BAD_REQUEST)

        lines_data = request.data.get('lines', [])
        if not lines_data:
            return Response({'error': 'lines are required'}, status=status.HTTP_400_BAD_REQUEST)

        lines = []
        for ld in lines_data:
            lines.append(ReceiveLine(
                po_line_id=ld['po_line_id'],
                qty=ld['qty'],
                warehouse_code=ld['warehouse_code'],
                unit_cost=ld.get('unit_cost'),
                lot=ld.get('lot'),
                serial_batch=ld.get('serial_batch')
            ))

        try:
            result = receive_purchase_order(po, receipt_no, lines)
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def totals(self, request, pk=None):
        """Get detailed totals for purchase order."""
        po = self.get_object()
        totals = po.update_sell_cost_totals(persist=False)
        return Response(totals)


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice transactions."""

    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'customer_id', 'vendor_id']

    @action(detail=True, methods=['post'])
    def apply_payment(self, request, pk=None):
        """Apply payment to invoice."""
        invoice = self.get_object()
        return Response({'message': 'Payment application endpoint - implementation needed'})

    @action(detail=True, methods=['get'])
    def payment_status(self, request, pk=None):
        """Get payment status for invoice."""
        invoice = self.get_object()
        return Response({'message': 'Payment status endpoint - implementation needed'})


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for Payment transactions."""

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payment_method', 'gateway', 'contact', 'invoice']

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process payment through gateway."""
        payment = self.get_object()
        return Response({'message': 'Payment processing endpoint - implementation needed'})

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Process refund."""
        payment = self.get_object()
        return Response({'message': 'Refund endpoint - implementation needed'})


__all__ = [
    'ProposalViewSet',
    'SalesOrderViewSet',
    'PurchaseOrderViewSet',
    'InvoiceViewSet',
    'PaymentViewSet',
]