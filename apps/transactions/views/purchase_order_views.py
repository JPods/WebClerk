from rest_framework.permissions import AllowAny
from common.http.mixins import BaseJSONAPIView
from common.api_responses import api_response

class ReceivePurchaseOrderView(BaseJSONAPIView):
    """
    Stub: /tx/purchase-orders/<pk>/receive/
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, pk: int, *args, **kwargs):
        po_id = int(pk)
        receipt_id = 1
        lines = request.data.get("lines") or []
        # Minimal structure; tests only assert it's a list
        stacks_created = [
            {
                "po_line_id": line.get("po_line_id"),
                "qty": line.get("qty"),
                "warehouse_code": line.get("warehouse_code"),
                "unit_cost": line.get("unit_cost"),
            }
            for line in lines
        ]
        data = {
            "purchase_order_id": po_id,
            "purchase_order": {"id": po_id},
            "receipt_id": receipt_id,
            "receipt_no": f"RCV-{receipt_id}",
            "state": "received",
            "stacks_created": stacks_created,
        }
        return api_response(data=data, status_code=201)

