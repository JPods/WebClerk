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
    filterset_fields = ['status', 'id_customer', 'id_vendor']

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
    filterset_fields = ['status', 'id_customer', 'id_vendor', 'order_no']

    @action(detail=True, methods=['post'])
    def convert_to_invoice(self, request, pk=None):
        """Convert order to invoice."""
        order = self.get_object()
        return Response({'message': 'Conversion endpoint - implementation needed'})

    @action(detail=True, methods=['post'])
    def create_purchase_order(self, request, pk=None):
        """Create purchase order from sales order."""
        order = self.get_object()
        return Response({'message': 'PO creation endpoint - implementation needed'})

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
    filterset_fields = ['status', 'id_customer', 'id_vendor', 'po_no']

    @action(detail=True, methods=['post'])
    def receive_goods(self, request, pk=None):
        """Record receipt of goods."""
        po = self.get_object()
        return Response({'message': 'Goods receipt endpoint - implementation needed'})


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice transactions."""

    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'id_customer', 'id_vendor']

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