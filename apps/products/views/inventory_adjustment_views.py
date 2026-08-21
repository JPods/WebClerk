"""Inventory adjustment API — always through Pending, one path, one audit trail."""
from __future__ import annotations

import logging
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone

from common.api_responses import api_response
from apps.core.models import Pending
from apps.products.models.inventory_layer import InventoryLayer

logger = logging.getLogger(__name__)

REASON_CODES = [
    'cycle_count', 'damage', 'return', 'shrinkage',
    'correction', 'receipt', 'bom_build', 'bom_consume', 'other',
]


class InventoryAdjustmentView(APIView):
    """POST /api/products/inventory/adjust/

    Apply one or more inventory adjustments. Every adjustment creates a
    Pending record which tries to apply itself on save. If the item is
    locked, celery picks it up later. One path, one audit trail.

    Body: {
        "warehouse_id": int,
        "lines": [
            {"item_id": int, "qty": number, "reason": str, "notes": str},
            ...
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        warehouse_id = request.data.get('warehouse_id')
        lines = request.data.get('lines', [])

        if not warehouse_id:
            return api_response(success=False, status_code=400, message='warehouse_id required')
        if not lines:
            return api_response(success=False, status_code=400, message='lines required')

        results = []
        applied_count = 0
        pending_count = 0

        for line in lines:
            item_id = line.get('item_id')
            qty = line.get('qty', 0)
            reason = line.get('reason', 'other')
            notes = line.get('notes', '')

            if not item_id or qty == 0:
                continue

            if reason not in REASON_CODES:
                reason = 'other'

            qty_decimal = Decimal(str(qty))

            # Create Pending — try_apply fires automatically in save()
            pending = Pending.objects.create(
                model_name='item',
                record_id=str(item_id),
                purpose='inventory_line_add',
                name=f'Adjustment {reason}: item {item_id}',
                changes={
                    'on_hand': float(qty_decimal),
                    'item_id': item_id,
                    'warehouse_id': warehouse_id,
                    'reason': reason,
                    'notes': notes,
                    'user': request.user.username if request.user else '',
                },
            )

            applied = pending.is_processed()
            if applied:
                applied_count += 1
            else:
                pending_count += 1

            results.append({
                'item_id': item_id,
                'pending_id': pending.pk,
                'applied': applied,
                'qty_adjusted': float(qty_decimal),
                'reason': reason,
            })

        return api_response(data={
            'applied': applied_count,
            'pending': pending_count,
            'lines': results,
        })


class InventoryAdjustmentHistoryView(APIView):
    """GET /api/products/inventory/adjustments/?item_id=N

    Return adjustment history for an item.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item_id')
        limit = int(request.query_params.get('limit', 50))

        if not item_id:
            return api_response(success=False, status_code=400, message='item_id required')

        rows = (Pending.objects
                .filter(model_name='item', record_id=str(item_id))
                .order_by('-dt_created')[:limit])

        results = []
        for r in rows:
            data = r.changes if isinstance(r.changes, dict) else {}
            results.append({
                'id': r.pk,
                'item_id': int(r.record_id),
                'purpose': r.purpose,
                'changes': data,
                'processed': r.is_processed(),
                'reason': data.get('reason', ''),
                'notes': data.get('notes', ''),
                'user': data.get('user', ''),
                'dt_created': r.dt_created,
                'dt_processed': r.dt_processed,
            })

        return api_response(data=results)


class InventoryLayersView(APIView):
    """GET /api/products/inventory/layers/?item_id=N

    Return FIFO/LIFO cost layers for an item, grouped by warehouse.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item_id')
        if not item_id:
            return api_response(success=False, status_code=400, message='item_id required')

        layers = (InventoryLayer.objects
                  .filter(item_id=item_id, is_deleted=False)
                  .select_related('warehouse')
                  .order_by('warehouse__name', 'dt_created'))

        results = []
        for layer in layers:
            qty = layer.quantity or {}
            cost = layer.cost or {}
            results.append({
                'id': layer.pk,
                'warehouse_id': layer.warehouse_id,
                'warehouse_name': layer.warehouse.name if layer.warehouse else '',
                'warehouse_code': layer.warehouse.code if layer.warehouse else '',
                'lot': layer.lot,
                'received': qty.get('received', 0),
                'issued': qty.get('issued', 0),
                'scrapped': qty.get('scrapped', 0),
                'remaining': float(layer.remaining_qty()),
                'unit_po': cost.get('unit_po', 0),
                'landed': cost.get('landed', 0),
                'moving_avg': cost.get('moving_avg', 0),
                'fifo_snapshot': cost.get('fifo_snapshot', 0),
                'lifo_snapshot': cost.get('lifo_snapshot', 0),
                'freight': cost.get('freight', 0),
                'duty': cost.get('duty', 0),
                'currency': cost.get('currency', 'USD'),
                'is_locked': layer.is_locked,
                'dt_created': layer.dt_created.isoformat() if layer.dt_created else None,
                'source_doc_type': layer.source_doc_type,
                'source_doc_id': layer.source_doc_id,
            })

        return api_response(data=results)


class InventoryBOMAdjustView(APIView):
    """POST /api/products/inventory/adjust-bom/

    Adjust inventory for a BOM parent — explodes children and adjusts each.
    qty > 0 = build (consume children, receive parent)
    qty < 0 = unbuild (issue parent, receive children)

    Body: {"item_id": int, "warehouse_id": int, "qty": int, "reason": str}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.products.models.bill_of_material import BillOfMaterial

        item_id = request.data.get('item_id')
        warehouse_id = request.data.get('warehouse_id')
        qty = request.data.get('qty', 0)
        reason = request.data.get('reason', 'bom_build')

        if not item_id or not warehouse_id or qty == 0:
            return api_response(success=False, status_code=400,
                                message='item_id, warehouse_id, and non-zero qty required')

        # Get BOM children
        bom_lines = BillOfMaterial.objects.filter(
            parent_item_id=item_id, is_deleted=False
        ).select_related('child_item')

        if not bom_lines.exists():
            return api_response(success=False, status_code=400,
                                message='No BOM found for this item')

        build_qty = Decimal(str(qty))
        adjustments = []

        with transaction.atomic():
            # Build (qty > 0): consume children, receive parent
            # Unbuild (qty < 0): issue parent, receive children
            for bom in bom_lines:
                child_qty = Decimal(str(bom.quantity)) * abs(build_qty)
                scrap = Decimal(str(bom.scrap_factor or 0))
                child_qty_with_scrap = child_qty * (1 + scrap)

                if build_qty > 0:
                    # Building: consume children (negative adjustment)
                    signed_child_qty = -child_qty_with_scrap
                else:
                    # Unbuilding: return children (positive adjustment)
                    signed_child_qty = child_qty_with_scrap

                adjustments.append({
                    'item_id': bom.child_item_id,
                    'qty': float(signed_child_qty),
                    'reason': 'bom_consume' if build_qty > 0 else 'bom_build',
                    'notes': f'BOM {"build" if build_qty > 0 else "unbuild"}: parent item {item_id} x {qty}',
                })

            # Parent adjustment (opposite of children)
            adjustments.append({
                'item_id': item_id,
                'qty': float(build_qty),
                'reason': reason,
                'notes': f'BOM {"build" if build_qty > 0 else "unbuild"}: {len(bom_lines)} components',
            })

        # Use the regular adjustment endpoint logic
        request._request.method = 'POST'
        request._full_data = {
            'warehouse_id': warehouse_id,
            'lines': adjustments,
        }
        return InventoryAdjustmentView().post(request)
