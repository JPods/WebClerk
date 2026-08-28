"""Serial number API endpoints.

WC2 never implemented WCapi for serials — we built it first in WC3.
All operations go through serial_services.py.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from rest_framework.views import APIView
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.products.models.serial import Serial
from apps.products.models.item import Item
from apps.products.services.serial import serial_ops as svc
from common.api_responses import api_response
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers


class SerialListByItemView(APIView):
    """List all serials for an item, optionally filtered by status."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_serial_list_by_item",
        parameters=[
            OpenApiParameter(name='status', description='Filter by status (available, issued, etc.)', required=False, type=str),
        ],
    )
    def get(self, request, item_id: int):
        get_object_or_404(Item, pk=item_id)
        status_filter = request.query_params.get('status')
        serials = svc.list_by_item(item_id, status=status_filter)
        data = [{
            'id': s.id, 'serial_ida': s.serial_ida, 'model_ida': s.model_ida,
            'status': s.status, 'item_ida': s.item_ida, 'description': s.description,
            'warranty': s.warranty, 'config': s.config,
            'refs': s.refs,
        } for s in serials]
        return api_response(data={'results': data, 'total': len(data)})


class SerialReceiveView(APIView):
    """Receive a serialized unit on a PO."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_receive")
    def post(self, request, item_id: int):
        get_object_or_404(Item, pk=item_id)
        d = request.data
        serial = svc.receive_serial(
            item_id=item_id,
            serial_number=d.get('serial_number', ''),
            vendor_id=d.get('vendor_id'),
            po_id=d.get('po_id'),
            po_line_id=d.get('po_line_id'),
            model_number=d.get('model_number', ''),
            cost=Decimal(str(d['cost'])) if d.get('cost') else None,
            warranty_days=int(d.get('warranty_days', 0)),
            site=d.get('site'),
        )
        return api_response(data={'id': serial.id, 'serial_ida': serial.serial_ida, 'status': serial.status},
                            status_code=201, message='Serial received')


class SerialIssueView(APIView):
    """Issue a serial to a sale (invoice/order)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_issue")
    def post(self, request, serial_id: int):
        get_object_or_404(Serial, pk=serial_id)
        d = request.data
        serial = svc.issue_to_sale(
            serial_id=serial_id,
            customer_id=d.get('customer_id'),
            invoice_id=d.get('invoice_id'),
            invoice_line_id=d.get('invoice_line_id'),
            order_id=d.get('order_id'),
            price=Decimal(str(d['price'])) if d.get('price') else None,
            discount=Decimal(str(d['discount'])) if d.get('discount') else None,
        )
        return api_response(data={'id': serial.id, 'status': serial.status, 'warranty': serial.warranty},
                            message='Serial issued')


class SerialReturnView(APIView):
    """Return a serial from a sale."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_return")
    def post(self, request, serial_id: int):
        get_object_or_404(Serial, pk=serial_id)
        d = request.data
        serial = svc.return_from_sale(
            serial_id=serial_id,
            reason=d.get('reason', 'Customer return'),
            invoice_id=d.get('invoice_id'),
        )
        return api_response(data={'id': serial.id, 'status': serial.status}, message='Serial returned')


class SerialReferenceView(APIView):
    """Attach a customer-owned serial to a document without formal receive."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_reference")
    def post(self, request, item_id: int):
        get_object_or_404(Item, pk=item_id)
        d = request.data
        serial = svc.reference_existing(
            item_id=item_id,
            serial_number=d.get('serial_number', ''),
            customer_id=d.get('customer_id'),
            document_type=d.get('document_type', ''),
            document_id=d.get('document_id'),
            remaining_warranty_days=int(d.get('remaining_warranty_days', 0)),
        )
        return api_response(data={'id': serial.id, 'serial_ida': serial.serial_ida, 'status': serial.status},
                            status_code=201, message='Serial referenced')


class SerialHistoryView(APIView):
    """Full event history for a serial unit."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_history")
    def get(self, request, serial_id: int):
        get_object_or_404(Serial, pk=serial_id)
        logs = svc.get_history(serial_id)
        data = [{
            'id': l.id, 'action': l.action, 'dt': l.dt, 'config': l.config,
        } for l in logs]
        return api_response(data={'results': data, 'total': len(data)})


class SerialSearchView(APIView):
    """Search serials by serial number, customer, or vendor."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_serial_search",
        parameters=[
            OpenApiParameter(name='serial', description='Serial number search', required=False, type=str),
            OpenApiParameter(name='customer_id', description='Customer ID', required=False, type=int),
            OpenApiParameter(name='vendor_id', description='Vendor ID', required=False, type=int),
        ],
    )
    def get(self, request):
        serial_num = request.query_params.get('serial')
        customer_id = request.query_params.get('customer_id')
        vendor_id = request.query_params.get('vendor_id')

        if serial_num:
            results = svc.search_by_serial_number(serial_num)
        elif customer_id:
            results = svc.search_by_customer(int(customer_id))
        elif vendor_id:
            results = svc.search_by_vendor(int(vendor_id))
        else:
            return api_response(success=False, status_code=400, message='Provide serial, customer_id, or vendor_id')

        data = [{
            'id': s.id, 'serial_ida': s.serial_ida, 'item_ida': s.item_ida,
            'status': s.status, 'description': s.description,
            'warranty': s.warranty, 'refs': s.refs,
        } for s in results]
        return api_response(data={'results': data, 'total': len(data)})


class SerialWarrantyView(APIView):
    """Find serials with warranty expiring or expired."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_serial_warranty",
        parameters=[
            OpenApiParameter(name='days_ahead', description='Days ahead to check (default 30)', required=False, type=int),
            OpenApiParameter(name='expired', description='Show expired instead of expiring', required=False, type=bool),
        ],
    )
    def get(self, request):
        expired = request.query_params.get('expired', '').lower() == 'true'
        if expired:
            results = svc.warranty_expired()
        else:
            days = int(request.query_params.get('days_ahead', 30))
            results = svc.warranty_due(days)

        data = [{
            'id': s.id, 'serial_ida': s.serial_ida, 'item_ida': s.item_ida,
            'status': s.status, 'warranty': s.warranty,
        } for s in results]
        return api_response(data={'results': data, 'total': len(data)})


class SerialStatusChangeView(APIView):
    """Generic status change with audit logging."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_serial_status_change")
    def post(self, request, serial_id: int):
        get_object_or_404(Serial, pk=serial_id)
        d = request.data
        serial = svc.change_status(serial_id, d.get('status', ''), reason=d.get('reason', ''))
        return api_response(data={'id': serial.id, 'status': serial.status}, message='Status changed')
