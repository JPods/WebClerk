from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.serializers.invoice_serializers import InvoiceSerializer, InvoiceLineSerializer
from apps.transactions.services.order_to_invoice import transfer_order_to_invoice
from apps.transactions.services.payment_pending import apply_payment_to_invoice
from apps.transactions.services.payment_application import get_invoice_payment_status


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Invoice. Writes go through /wcapi/save/."""

    queryset = Invoice.objects.active()
    serializer_class = InvoiceSerializer

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

        try:
            result = apply_payment_to_invoice(
                payment_id=int(payment_id),
                invoice_id=invoice.pk,
                amount=amount or 0,
            )
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


class InvoiceLineViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for InvoiceLine. Writes go through /wcapi/save/."""

    queryset = InvoiceLine.objects.active()
    serializer_class = InvoiceLineSerializer

    def get_queryset(self):
        """Filter by invoice if specified."""
        queryset = self.queryset
        invoice_id = self.request.query_params.get('invoice_id')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset