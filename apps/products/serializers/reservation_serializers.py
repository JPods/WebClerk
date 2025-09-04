from __future__ import annotations

from rest_framework import serializers
from apps.products.models.inventory_reservation import InventoryReservation


class InventoryReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReservation
        fields = [
            'id', 'item', 'warehouse', 'stack', 'qty', 'state', 'expires_at',
            'committed_at', 'released_at', 'reason', 'context', 'created_dt', 'modified_dt'
        ]
        read_only_fields = ['state', 'committed_at', 'released_at', 'created_dt', 'modified_dt']

class ReservationCreateSerializer(serializers.Serializer):
    stack_id = serializers.IntegerField(required=True)
    qty = serializers.DecimalField(max_digits=14, decimal_places=4)
    ttl_seconds = serializers.IntegerField(required=False, min_value=1, default=900)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=80)
    ctx = serializers.JSONField(required=False)

class ReservationActionSerializer(serializers.Serializer):
    reservation_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['commit', 'release'])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=80)
