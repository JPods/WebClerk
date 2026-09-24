from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from common.base_views import BaseOptimisticDetailView
from apps.core.services.record_serialize import visible_queryset
from apps.transactions.models import (
    Quote, Order, Purchase, Invoice
)
from apps.transactions.serializers import (
    QuoteSerializer, OrderSerializer, PurchaseSerializer,
    InvoiceSerializer
)
from apps.transactions.services.convert import convert_quote_to_order as quote_to_order
from apps.transactions.services.convert import convert_order_to_invoice as order_to_invoice
from apps.transactions.services import inventory_flow
from apps.transactions.services.transaction_flow import receive_purchase, ReceiveLine
from apps.transactions.services.pricing.commission_compute import populate_transaction_commission


def _require_staff(request):
    """Return error Response if user is not staff, else None."""
    user = getattr(request, 'user', None)
    if not user or not (user.is_staff or user.is_superuser):
        return Response(
            {'error': 'Staff access required'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


class _VisibleActions(viewsets.GenericViewSet):
    """Actions on one transaction, looked up through the one read channel.

    No list and no retrieve: reads go through /wcapi/get/ (Bill, 2026-09-23 — all gets
    flow through one channel). get_object() sees only the rows visible_queryset shows
    this user, so an action cannot reach a record its caller could not read.
    """
    model_key = ''

    def get_queryset(self):
        return visible_queryset(self.model_key, user=self.request.user)[1]


class QuoteViewSet(_VisibleActions):
    """Actions on a quote. Writes go through /wcapi/save/."""

    model_key = 'quote'
    serializer_class = QuoteSerializer

    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convert quote to order."""
        quote = self.get_object()
        try:
            result = quote_to_order.transfer_quote_to_order(
                quote=quote,
                line_ids=request.data.get('line_ids'),
                transfer_all=request.data.get('transfer_all', True),
                order_status=request.data.get('order_status', 'confirmed'),
                preserve_quote=request.data.get('preserve_quote', True),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['post'])
    def populate_commission(self, request, pk=None):
        """Populate commission from customer's rep assignments. Staff only."""
        denied = _require_staff(request)
        if denied:
            return denied
        quote = self.get_object()
        try:
            result = populate_transaction_commission(quote.pk, 'quote')
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(_VisibleActions):
    """Actions on a order. Writes go through /wcapi/save/."""

    model_key = 'order'
    serializer_class = OrderSerializer

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
        from apps.transactions.services.convert.convert_order_to_purchase import transfer_order_to_purchase

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

    @action(detail=True, methods=['post'])
    def populate_commission(self, request, pk=None):
        """Populate commission from customer's rep assignments. Staff only."""
        denied = _require_staff(request)
        if denied:
            return denied
        order = self.get_object()
        try:
            result = populate_transaction_commission(order.pk, 'order')
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseViewSet(_VisibleActions):
    """Actions on a purchase. Writes go through /wcapi/save/."""

    model_key = 'purchase'
    serializer_class = PurchaseSerializer

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


class InvoiceViewSet(_VisibleActions):
    """Actions on a invoice. Writes go through /wcapi/save/."""

    model_key = 'invoice'
    serializer_class = InvoiceSerializer

    @action(detail=True, methods=['get'])
    def cash_status(self, request, pk=None):
        """Get cash status for invoice."""
        invoice = self.get_object()
        return Response({'message': 'Cash status endpoint - implementation needed'})

    @action(detail=True, methods=['post'])
    def populate_commission(self, request, pk=None):
        """Populate commission from customer's rep assignments. Staff only."""
        denied = _require_staff(request)
        if denied:
            return denied
        invoice = self.get_object()
        try:
            result = populate_transaction_commission(invoice.pk, 'invoice')
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


__all__ = [
    'QuoteViewSet',
    'OrderViewSet',
    'PurchaseViewSet',
    'InvoiceViewSet',
]