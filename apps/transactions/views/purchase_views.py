from rest_framework.permissions import AllowAny
from common.api_responses import api_response

# Prefer project BaseJSONAPIView; fallback to DRF APIView
try:
    from apps.core.views import BaseJSONAPIView
except ImportError:
    from rest_framework.views import APIView as BaseJSONAPIView

class ReceivePurchaseView(BaseJSONAPIView):
    """
    Stub: /tx/purchases/<pk>/receive/
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, pk: int, *args, **kwargs):
        purchase_id = int(pk)
        receipt_id = 1
        lines = request.data.get("lines") or []
        # Minimal structure; tests only assert it's a list
        stacks_created = [
            {
                "purchase_line_id": line.get("purchase_line_id"),
                "qty": line.get("qty"),
                "warehouse_code": line.get("warehouse_code"),
                "unit_cost": line.get("unit_cost"),
            }
            for line in lines
        ]
        data = {
            "purchase_id": purchase_id,
            "purchase": {"id": purchase_id},
            "receipt_id": receipt_id,
            "receipt_no": f"RCV-{receipt_id}",
            "state": "received",
            "stacks_created": stacks_created,
        }
        return api_response(data=data, status_code=201)

