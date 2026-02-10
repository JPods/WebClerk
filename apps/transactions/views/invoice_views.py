from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.serializers.invoice_serializers import InvoiceSerializer, InvoiceLineSerializer
from apps.core.services import wcapi
from apps.transactions.services.order_to_invoice import transfer_order_to_invoice
from apps.transactions.services.payment_application import apply_payment_to_invoice, get_invoice_payment_status


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    REST API viewset for Invoice management.
    Uses WCAPI for all save operations to maintain consistency and security.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        return self.queryset

    def perform_create(self, serializer):
        """Create invoice using WCAPI save."""
        data = serializer.validated_data.copy()
        data['model_name'] = 'invoice'

        # Use WCAPI save for consistency
        result = wcapi.save_item('invoice', request=self.request, data=data)
        if result[1] == 'created':
            # Set the created instance on serializer for response
            instance = Invoice.objects.get(pk=result[0])
            serializer.instance = instance
        else:
            raise Exception("Failed to create invoice")

    def perform_update(self, serializer):
        """Update invoice using WCAPI save."""
        instance = self.get_object()
        data = serializer.validated_data.copy()
        data['model_name'] = 'invoice'
        data['id'] = instance.id

        # Use WCAPI save for consistency
        result = wcapi.save_item('invoice', request=self.request, data=data, id=instance.id)
        if result[1] == 'updated':
            # Refresh instance
            instance.refresh_from_db()
            serializer.instance = instance
        else:
            raise Exception("Failed to update invoice")

    @action(detail=True, methods=['post'])
    def convert_from_order(self, request, pk=None):
        """Convert sales order to invoice."""
        invoice = self.get_object()

        # Get order_id from request or refs
        order_id = request.data.get('order_id')
        if not order_id and invoice.refs:
            order_id = invoice.refs.get('source', {}).get('sales_order_id')

        if not order_id:
            return Response(
                {'error': 'order_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use the transfer service
        try:
            from apps.transactions.models import Order
            order = Order.objects.filter(pk=order_id).first()
            if not order:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
            result = transfer_order_to_invoice(order=order)
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def apply_payment(self, request, pk=None):
        """Apply a payment to this invoice."""
        invoice = self.get_object()
        payment_id = request.data.get('payment_id')
        amount = request.data.get('amount')

        if not payment_id:
            return Response(
                {'error': 'payment_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.transactions.models import Payment
        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = apply_payment_to_invoice(invoice, payment, amount)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def payment_status(self, request, pk=None):
        """Get payment status for this invoice."""
        invoice = self.get_object()
        status_data = get_invoice_payment_status(invoice)
        return Response(status_data)

    @action(detail=True, methods=['get'])
    def totals(self, request, pk=None):
        """Get detailed totals for invoice."""
        invoice = self.get_object()
        totals = invoice.update_sell_cost_totals(persist=False)
        return Response(totals)


class InvoiceLineViewSet(viewsets.ModelViewSet):
    """
    REST API viewset for Invoice Line management.
    Uses WCAPI for all save operations.
    """
    queryset = InvoiceLine.objects.all()
    serializer_class = InvoiceLineSerializer

    def get_queryset(self):
        """Filter by invoice if specified."""
        queryset = self.queryset
        invoice_id = self.request.query_params.get('invoice_id')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

    def perform_create(self, serializer):
        """Create invoice line using WCAPI save."""
        data = serializer.validated_data.copy()
        data['model_name'] = 'invoice_line'

        result = wcapi.save_item('invoice_line', request=self.request, data=data)
        if result[1] == 'created':
            instance = InvoiceLine.objects.get(pk=result[0])
            serializer.instance = instance
        else:
            raise Exception("Failed to create invoice line")

    def perform_update(self, serializer):
        """Update invoice line using WCAPI save."""
        instance = self.get_object()
        data = serializer.validated_data.copy()
        data['model_name'] = 'invoice_line'
        data['id'] = instance.id

        result = wcapi.save_item('invoice_line', request=self.request, data=data, id=instance.id)
        if result[1] == 'updated':
            instance.refresh_from_db()
            serializer.instance = instance
        else:
            raise Exception("Failed to update invoice line")

    def perform_destroy(self, instance):
        """Delete invoice line using WCAPI."""
        wcapi.delete_item('invoice_line', request=self.request, id=instance.id)