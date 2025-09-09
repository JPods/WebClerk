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
    sales_order_to_purchase_order,
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


class SalesOrderToPurchaseOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = SalesOrder.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Purchase order created")})
    def post(self, request, *args, **kwargs):
        so_id = kwargs.get('pk')
        so = SalesOrder.objects.filter(pk=so_id).first()
        if not so:
            return response.Response({'detail': 'Sales order not found'}, status=404)
        po = sales_order_to_purchase_order(so)
        return response.Response({'purchase_order_id': po.id, 'po_no': po.po_no}, status=status.HTTP_201_CREATED)  # type: ignore[attr-defined]


class LinkageCommentsAggregateView(APIView):
    permission_classes = [BasePermission]

    @extend_schema(responses={200: OpenApiResponse(description="Aggregated comments for linkage")})
    def get(self, request, *args, **kwargs):
        linkage_id = kwargs.get('linkage_id')
        from apps.docs.models.linkage import Linkage
        linkage = Linkage.objects.filter(pk=linkage_id).first()
        if not linkage:
            return response.Response({'detail': 'Linkage not found'}, status=404)
        # Aggregate comments across linked records (headers & lines) fetching their comments JSON if present
        aggregated: list[dict] = []
        links = (getattr(linkage, 'refs', {}) or {}).get('links', {})
        from apps.transactions.models.line_variants import (
            ProposalLine, SalesOrderLine, InvoiceLine, PurchaseOrderLine
        )
        line_models = [ProposalLine, SalesOrderLine, InvoiceLine, PurchaseOrderLine]
        if isinstance(links, dict):
            for id_list in links.values():
                if not isinstance(id_list, list):
                    continue
                for rec_id in id_list:
                    for lm in line_models:
                        obj = lm.objects.filter(pk=rec_id).first()
                        if obj and isinstance(getattr(obj, 'comments', {}), dict):
                            cm = getattr(obj, 'comments')
                            if any(v for v in cm.values() if isinstance(cm, dict)):
                                aggregated.append({
                                    'model': lm._meta.model_name,  # type: ignore[attr-defined]
                                    'id': rec_id,
                                    'comments': cm,
                                })
                            break
        linkage_comments = getattr(linkage, 'comments', {}) or {}
        # Normalize to ensure a 'general' bucket exists and that simple public/process fields nest under it.
        if 'general' not in linkage_comments or not isinstance(linkage_comments.get('general'), dict):
            # If legacy flat structure (public/process/partner/notes) elevate into general
            flat_keys = {'public', 'process', 'partner', 'notes'}
            if any(k in linkage_comments for k in flat_keys):
                general_block = {k: linkage_comments.get(k, '') for k in flat_keys}
                # Remove moved keys
                for k in flat_keys:
                    linkage_comments.pop(k, None)
                linkage_comments['general'] = general_block
            else:
                linkage_comments.setdefault('general', {})

        return response.Response({
            'linkage_id': linkage.id,  # type: ignore[attr-defined]
            'comments': linkage_comments,
            'items': aggregated
        }, status=200)


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
