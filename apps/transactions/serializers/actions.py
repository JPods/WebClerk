from __future__ import annotations

from typing import List
from decimal import Decimal
from rest_framework import serializers


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


class ReceivePurchaseOrderSerializer(serializers.Serializer):
    receipt_no = serializers.CharField(max_length=40)
    lines = ReceiveLineSerializer(many=True)
