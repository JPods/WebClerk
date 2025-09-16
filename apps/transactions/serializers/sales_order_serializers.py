from rest_framework import serializers
from apps.transactions.models import SalesOrder, SalesOrderLine


class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = ["id", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class SalesOrderLineSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=True)

    class Meta:
        model = SalesOrderLine
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
            parent = SalesOrder.objects.get(pk=parent_id)
        except SalesOrder.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid sales order id"})
        validated_data["parent"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = SalesOrder.objects.get(pk=parent_id)
            except SalesOrder.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid sales order id"})
            validated_data["parent"] = parent
        return super().update(instance, validated_data)
