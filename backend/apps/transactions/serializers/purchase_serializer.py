from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Purchase, PurchaseLine
from .helpers import _name_from_refs, BASE_RO
from .base_line_serializer import BaseLineSerializer
from .behaviors import (
    validate_customer_id as _validate_customer_id,
    validate_vendor_id as _validate_vendor_id,
    validate_customer_vendor_different,
    validate_status_transition,
)


class PurchaseLineRichSerializer(RoleAwareModelSerializer):
    """Rich serializer for nested display in PurchaseSerializer."""

    class Meta:
        model = PurchaseLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'purchase',
        ]
        read_only_fields = BASE_RO


class PurchaseLineSerializer(BaseLineSerializer):
    """CRUD serializer for PurchaseLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=Purchase.objects.all(), source='purchase')

    class Meta(BaseLineSerializer.Meta):
        model = PurchaseLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class PurchaseSerializer(RoleAwareModelSerializer):
    """Serializer for Purchase transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.cost, totals.balance.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = PurchaseLineRichSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'totals',
            'finance', 'flow', 'source', 'refs', 'metadata',
            'line_count', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'line_count', 'customer_name', 'vendor_name', 'lines']

    def get_customer_name(self, obj):
        return _name_from_refs(obj, 'customer')

    def get_vendor_name(self, obj):
        return _name_from_refs(obj, 'vendor')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'lines'):
            data['line_count'] = instance.lines.count()
        return data

    def validate_customer_id(self, value):
        return _validate_customer_id(value)

    def validate_vendor_id(self, value):
        return _validate_vendor_id(value)

    def validate_status(self, value):
        validate_status_transition(self.instance, value)
        return value

    def validate(self, data):
        validate_customer_vendor_different(data)
        return data
