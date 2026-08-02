"""Bulk inventory lookup for line card panels (L button, QuickQuote)."""
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework import permissions
from common.api_responses import api_response
from apps.products.models.item import Item


class BulkItemInventoryView(APIView):
    """GET /api/products/items/inventory/?ids=1,2,3

    Returns inventory summary for multiple items in a single call.
    Powers the line card "L" button (inventory peek) and QuickQuote panel.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids_param = request.query_params.get('ids', '')
        if not ids_param:
            return api_response(data=[], message='No ids provided')

        try:
            item_ids = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
        except ValueError:
            return api_response(success=False, status_code=400, message='Invalid ids parameter')

        if len(item_ids) > 200:
            return api_response(success=False, status_code=400, message='Max 200 items per request')

        items = Item.objects.filter(
            id__in=item_ids, is_deleted=False
        ).only('id', 'ida', 'name', 'quantity', 'price', 'config')

        results = []
        for item in items:
            qty = item.quantity if isinstance(item.quantity, dict) else {}
            price_data = item.price if isinstance(item.price, dict) else {}
            config = item.config if isinstance(item.config, dict) else {}

            results.append({
                'id': item.id,
                'ida': item.ida,
                'name': item.name,
                'available': qty.get('available'),
                'on_hand': qty.get('on_hand'),
                'on_so': qty.get('on_so'),
                'on_po': qty.get('on_po'),
                'on_wo': qty.get('on_wo'),
                'allocated': qty.get('allocated'),
                'lead_time': config.get('lead_time'),
                'price_retail': price_data.get('retail'),
                'price_wholesale': price_data.get('wholesale'),
                'cost_standard': (item.cost.get('standard') if isinstance(getattr(item, 'cost', None), dict) else None),
            })

        return api_response(data=results)
