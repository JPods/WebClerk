from __future__ import annotations

from typing import List
from decimal import Decimal
from rest_framework import serializers
from apps.transactions.models import WorkOrder, WorkOrderLine


class ConvertRequestSerializer(serializers.Serializer):
    # No fields needed currently; placeholder for future flags
    confirm = serializers.BooleanField(required=False, default=True)


class ReceiveLineSerializer(serializers.Serializer):
    po_line_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=14, decimal_places=4)
    warehouse_code = serializers.CharField(max_length=40)
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    lot = serializers.CharField(max_length=80, required=False, allow_blank=True)
    serial_batch = serializers.CharField(max_length=80, required=False, allow_blank=True)


class ReceivePurchaseSerializer(serializers.Serializer):
    receipt_no = serializers.CharField(max_length=40)
    lines = ReceiveLineSerializer(many=True)


class TransitionRequestSerializer(serializers.Serializer):
    """Generic transition payload for header/line state changes.

    Fields:
    - to: target status (validated per endpoint's model)
    - reason: optional free-text reason, stored in audit trail
    """
    to = serializers.CharField(max_length=40)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    depends_on = serializers.DictField(required=False, allow_empty=True)

    def validate_to(self, value: str) -> str:
        value = value.strip().lower()
        ctx = self.context or {}
        model = ctx.get('model')
        if model is WorkOrder:
            valid = {k for k, _ in WorkOrder.STATUS_CHOICES}
        elif model is WorkOrderLine:
            # WorkOrderLine currently inherits generic BaseLineModel without fixed STATUS_CHOICES;
            # accept any non-empty target for lines, or validate against header choices if provided in context.
            valid = set()
        else:
            valid = set()
        if valid and value not in valid:
            raise serializers.ValidationError(f"Invalid target status '{value}'")
        return value
