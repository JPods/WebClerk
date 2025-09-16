from rest_framework import serializers
from apps.transactions.models import Workorder, WorkorderLine


class WorkorderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workorder
        fields = ["id", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class WorkorderLineSerializer(serializers.ModelSerializer):
    # Require parent_id in API contracts; map to FK 'parent' internally
    parent_id = serializers.IntegerField(required=True)

    class Meta:
        model = WorkorderLine
        fields = [
            "id", "parent_id", "status", "price_level",
            "item", "quantity", "cost", "price", "tax", "action", "physical", "flow", "source",
            "dt_created", "dt_modified",
        ]
        read_only_fields = ["id", "dt_created", "dt_modified"]

    def create(self, validated_data):
        parent_id = validated_data.pop("parent_id", None)
        if parent_id is None:
            raise serializers.ValidationError({"parent_id": "This field is required."})
        try:
            parent = Workorder.objects.get(pk=parent_id)
        except Workorder.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid workorder id"})
        validated_data["parent"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = Workorder.objects.get(pk=parent_id)
            except Workorder.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid workorder id"})
            validated_data["parent"] = parent
        return super().update(instance, validated_data)
