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
                  .filter(item_id=item_id)
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
                'dt_created': layer.dt_created.isoformat() if layer.dt_created else None,
                'source_doc_type': layer.source_doc_type,
                'source_doc_id': layer.source_doc_id,
            })

        return api_response(data=results)


