from rest_framework import serializers
from apps.transactions.models import WorkOrder, WorkOrderLine


class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["id", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class WorkOrderLineSerializer(serializers.ModelSerializer):
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
