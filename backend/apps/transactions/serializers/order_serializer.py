from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Order, OrderLine
from apps.orgs.models import OrgBase
from .helpers import _name_from_refs, BASE_RO
from .base_line_serializer import BaseLineSerializer


class OrderLineRichSerializer(RoleAwareModelSerializer):
    """Rich serializer for nested display in OrderSerializer."""

    class Meta:
        model = OrderLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'price', 'order',
        ]
        read_only_fields = BASE_RO


class OrderLineSerializer(BaseLineSerializer):
    """CRUD serializer for OrderLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all(), source='order')

    class Meta(BaseLineSerializer.Meta):
        model = OrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class OrderLineParentIdSerializer(serializers.ModelSerializer):
    """Legacy parent_id-based CRUD serializer for OrderLine."""
    parent_id = serializers.IntegerField(required=True)
    action = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    flow = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)

    class Meta:
        model = OrderLine
        fields = [
            "id", "parent_id", "status", "price_level",
            "item", "quantity", "cost", "price", "tax", "action", "physical", "flow", "source",
            "dt_created", "dt_modified",
        ]
        read_only_fields = ["id", "dt_created", "dt_modified"]

    def create(self, validated_data):
        # Strip non-model fields
        for k in ("action", "flow", "source"):
            validated_data.pop(k, None)
        parent_id = validated_data.pop("parent_id", None)
        if parent_id is None:
            raise serializers.ValidationError({"parent_id": "This field is required."})
        try:
            parent = Order.objects.get(pk=parent_id)
        except Order.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid order id"})
        validated_data["order"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Strip non-model fields
        for k in ("action", "flow", "source"):
            validated_data.pop(k, None)
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = Order.objects.get(pk=parent_id)
            except Order.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid order id"})
            validated_data["order"] = parent
        return super().update(instance, validated_data)


class OrderSerializer(RoleAwareModelSerializer):
    """Serializer for Order transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.margin, totals.margin_pc.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = OrderLineRichSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'cost', 'sell', 'totals',
            'finance', 'flow', 'source', 'refs', 'prefs', 'metadata',
            'line_count', 'customer_name', 'vendor_name', 'lines',
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

    def validate_status(self, value):
        """Validate status transitions."""
        valid_statuses = ['planned', 'released', 'in_progress', 'hold', 'complete', 'canceled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_customer_id(self, value):
        """Validate customer exists."""
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Customer organization does not exist.")
        return value

    def validate_vendor_id(self, value):
        """Validate vendor exists."""
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Vendor organization does not exist.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")
        return data
