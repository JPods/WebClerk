from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Invoice, InvoiceLine
from .helpers import _name_from_refs, BASE_RO
from .base_line_serializer import BaseLineSerializer
from .behaviors import (
    validate_customer_id as _validate_customer_id,
    validate_vendor_id as _validate_vendor_id,
    validate_customer_vendor_different,
    validate_status_transition,
)


class InvoiceLineRichSerializer(RoleAwareModelSerializer):
    """Rich serializer for nested display in InvoiceSerializer."""

    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'price', 'invoice',
        ]
        read_only_fields = BASE_RO


class InvoiceLineSerializer(BaseLineSerializer):
    """CRUD serializer for InvoiceLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all(), source='invoice')

    class Meta(BaseLineSerializer.Meta):
        model = InvoiceLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class InvoiceLineParentIdSerializer(serializers.ModelSerializer):
    """Legacy parent_id-based CRUD serializer for InvoiceLine."""
    # Require parent_id in API contracts; map to FK 'parent' internally
    parent_id = serializers.IntegerField(required=True)
    # Accept arbitrary action/flow/source/physical without binding to model
    action = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    flow = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    physical = serializers.BooleanField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            "id", "parent_id", "status", "price_level",
            "item", "quantity", "cost", "price", "tax",
            "action", "physical", "flow", "source",
            "dt_created", "dt_modified",
        ]
        read_only_fields = ["id", "dt_created", "dt_modified"]

    def create(self, validated_data):
        # Strip non-model fields
        for k in ("action", "flow", "source", "physical"):
            validated_data.pop(k, None)
        parent_id = validated_data.pop("parent_id", None)
        if parent_id is None:
            raise serializers.ValidationError({"parent_id": "This field is required."})
        try:
            parent = Invoice.objects.get(pk=parent_id)
        except Invoice.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid invoice id"})
        validated_data["invoice"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Strip non-model fields
        for k in ("action", "flow", "source", "physical"):
            validated_data.pop(k, None)
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = Invoice.objects.get(pk=parent_id)
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid invoice id"})
            validated_data["invoice"] = parent
        return super().update(instance, validated_data)


class InvoiceSerializer(RoleAwareModelSerializer):
    """Serializer for Invoice transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.balance, totals.margin.
    """

    line_count = serializers.SerializerMethodField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = InvoiceLineRichSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'cost', 'sell', 'totals',
            'finance', 'flow', 'source', 'refs', 'prefs', 'metadata',
            'line_count', 'customer_name', 'vendor_name', 'lines',
            'dt_created', 'dt_modified', 'version',
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'line_count', 'customer_name', 'vendor_name', 'lines']

    def get_line_count(self, instance):
        if hasattr(instance, 'lines'):
            return instance.lines.count()
        return 0

    def get_customer_name(self, obj):
        return _name_from_refs(obj, 'customer')

    def get_vendor_name(self, obj):
        return _name_from_refs(obj, 'vendor')

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
