from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.http.mixins import BaseJSONAPIView

class ReservationListView(BaseJSONAPIView):
    """
    Stub list/create endpoint for inventory reservations.
    Accepts POST with stack_id and qty, returns 201 with a minimal payload.
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        payload = request.data or {}
        stack_id = payload.get("stack_id")
        qty = payload.get("qty")
        # Return a minimal stubbed reservation
        data = {
            "id": 1,
            "stack_id": stack_id,
            "qty": qty,
            "status": "pending",
            "version": 1,
        }
        return Response(data, status=201)

class ReservationDetailView(BaseJSONAPIView):
    """
    Stub detail endpoint for inventory reservations.
    """
    permission_classes = [AllowAny]
    http_method_names = ["get", "patch", "options", "head"]

    def get(self, request, pk: int, *args, **kwargs):
        # Return a minimal stubbed reservation record
        data = {"id": int(pk), "status": "pending", "version": 1}
        return Response(data, status=200)

    def patch(self, request, pk: int, *args, **kwargs):
        # Optimistic no-op: echo back with +1 version
        body = request.data or {}
        ver = body.get("version", 1)
        data = {"id": int(pk), "status": "pending", "version": int(ver) + 1}
        return Response(data, status=200)