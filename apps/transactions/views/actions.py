from __future__ import annotations

from rest_framework import status, response
from typing import Any, Dict, cast
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.transactions.models.line_variants import Proposal, SalesOrder, PurchaseOrder
from apps.transactions.serializers.actions import (
    ConvertRequestSerializer,
    ReceivePurchaseOrderSerializer,
)
from apps.transactions.services.flow import (
    proposal_to_sales_order,
    sales_order_to_invoice,
    receive_purchase_order,
    ReceiveLine,
)
from apps.transactions.views.line_views import BasePermission


class ProposalToSalesOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = Proposal.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Sales order created")})
    def post(self, request, *args, **kwargs):
        proposal_id = kwargs.get('pk')
        proposal = Proposal.objects.filter(pk=proposal_id).first()
        if not proposal:
            return response.Response({'detail': 'Proposal not found'}, status=404)
        so = proposal_to_sales_order(proposal)
        return response.Response({'sales_order_id': so.id, 'order_no': so.order_no}, status=status.HTTP_201_CREATED)  # type: ignore[attr-defined]


class SalesOrderToInvoiceView(APIView):
    permission_classes = [BasePermission]
    queryset = SalesOrder.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Invoice created")})
    def post(self, request, *args, **kwargs):
        so_id = kwargs.get('pk')
        so = SalesOrder.objects.filter(pk=so_id).first()
        if not so:
            return response.Response({'detail': 'Sales order not found'}, status=404)
        inv = sales_order_to_invoice(so)
        return response.Response({'invoice_id': inv.id, 'invoice_no': inv.invoice_no}, status=status.HTTP_201_CREATED)  # type: ignore[attr-defined]


class ReceivePurchaseOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = PurchaseOrder.objects.all()

    @extend_schema(request=ReceivePurchaseOrderSerializer, responses={201: OpenApiResponse(description="Receipt posted & inventory updated")})
    def post(self, request, *args, **kwargs):
        po_id = kwargs.get('pk')
        po = PurchaseOrder.objects.filter(pk=po_id).first()
        if not po:
            return response.Response({'detail': 'Purchase order not found'}, status=404)
        ser = ReceivePurchaseOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd: Dict[str, Any] = cast(Dict[str, Any], ser.validated_data)  # dict-like with required keys
        receipt_no = str(vd['receipt_no'])
        line_payloads = list(vd['lines'])
        lines = [ReceiveLine(**ln) for ln in line_payloads]
        summary = receive_purchase_order(po, receipt_no, lines)
        return response.Response(summary, status=status.HTTP_201_CREATED)
