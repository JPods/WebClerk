from rest_framework import serializers
from apps.transactions.models import Order, OrderLine


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class OrderLineSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=True)

    class Meta:
        model = OrderLine
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
            parent = Order.objects.get(pk=parent_id)
        except Order.DoesNotExist:
            raise serializers.ValidationError({"parent_id": "Invalid order id"})
        validated_data["parent"] = parent
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "parent_id" in validated_data:
            parent_id = validated_data.pop("parent_id")
            try:
                parent = Order.objects.get(pk=parent_id)
            except Order.DoesNotExist:
                raise serializers.ValidationError({"parent_id": "Invalid order id"})
            validated_data["parent"] = parent
        return super().update(instance, validated_data)

