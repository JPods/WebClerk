from __future__ import annotations

from django.apps import apps as django_apps
from rest_framework import serializers


def _model(name: str):
    return django_apps.get_model("products", name)


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Item")
        fields = "__all__"


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Variant")
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Service")
        fields = "__all__"


class ItemXrefSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("ItemXref")
        fields = "__all__"


class SerialSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Serial")
        fields = "__all__"


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Specification")
        fields = "__all__"


class BillOfMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("BillOfMaterial")
        fields = "__all__"


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Catalog")
        fields = "__all__"


class OrgItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("OrgItem")
        fields = "__all__"


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Warehouse")
        fields = "__all__"


class UsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Usage")
        fields = "__all__"


class InventoryReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("InventoryReservation")
        fields = "__all__"


class FlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Flow")
        fields = "__all__"