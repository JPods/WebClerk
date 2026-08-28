from rest_framework import serializers
from apps.transactions.models import WorkOrder, WorkOrderLine
from .base_line_serializer import BaseLineSerializer
from .behaviors import (
    validate_customer_id as _validate_customer_id,
    validate_vendor_id as _validate_vendor_id,
    validate_customer_vendor_different,
    validate_status_transition,
)


class WorkOrderSerializer(serializers.ModelSerializer):
    line_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id', 'contact_id',
            'totals', 'refs', 'prefs', 'metadata',
            'line_count',
            'dt_created', 'dt_modified', 'version',
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'line_count']

    def get_line_count(self, instance):
        if hasattr(instance, 'lines'):
            return instance.lines.count()
        return 0

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


class WorkOrderLineSerializer(BaseLineSerializer):
    """CRUD serializer for WorkOrderLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), source='workorder')

    class Meta(BaseLineSerializer.Meta):
        model = WorkOrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class WorkOrderLineParentIdSerializer(serializers.ModelSerializer):
    """Legacy parent_id-based CRUD serializer for WorkOrderLine."""
    # Require parent_id in API contracts; map to FK internally
    parent_id = serializers.IntegerField(required=True)
    action = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    flow = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)

    class Meta:
        model = WorkOrderLine
        fields = [
            "id", "parent_id", "status", "price_level",
            "item", "quantity", "cost", "tax", "action", "physical", "flow", "source",
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
            parent = WorkOrder.objects.get(pk=parent_id)
        except WorkOrder.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid workorder id"})
        validated_data["workorder"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Strip non-model fields
        for k in ("action", "flow", "source"):
            validated_data.pop(k, None)
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = WorkOrder.objects.get(pk=parent_id)
            except WorkOrder.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid workorder id"})
            validated_data["workorder"] = parent
        return super().update(instance, validated_data)
