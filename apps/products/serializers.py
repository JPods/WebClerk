from __future__ import annotations

from django.apps import apps as django_apps
from rest_framework import serializers


def _model(name: str):
    return django_apps.get_model("products", name)


# -- system fields inherited from BaseModel (read-only for all serializers) --
_BASE_RO = [
    "id", "uuid", "dt_created", "dt_modified", "version",
    "is_deleted", "is_archived", "metadata", "refs", "prefs",
    "actions", "comments", "health_rating",
]


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Item")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "stats", "name", "sku", "qr_code", "kind", "uom", "base_uom",
            "description", "gls", "flags", "price", "cost", "tax_code",
            "specification_id", "catalog", "quantity", "row_version",
        ]
        read_only_fields = _BASE_RO


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Variant")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "item_ida", "description", "item", "parent_item",
            "canonical_key", "attrs", "set_uuid", "variant_uuid",
        ]
        read_only_fields = _BASE_RO


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Service")
        fields = [
            "id", "uuid", "ida", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "comments", "health_rating",
            "item_id", "status", "description", "purpose", "category",
            "display", "actions", "billing", "process", "travel",
            "default_duration_minutes", "row_version", "billing_audit",
        ]
        read_only_fields = _BASE_RO


class ItemXrefSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("ItemXref")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "item_id", "status", "source", "source_id", "source_model_name",
            "source_name", "external_sku", "external_uuid", "cost", "is_preferred",
        ]
        read_only_fields = _BASE_RO


class SerialSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Serial")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "item_id", "item_ida", "description", "serial_ida", "model_ida",
            "warranty", "status", "site", "inventory_layer_id", "data", "qr_code",
        ]
        read_only_fields = _BASE_RO


# NOTE: Specification model does not exist in the products app.
# Serializer removed to prevent import crash. Re-add when model is created.


class BillOfMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("BillOfMaterial")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "parent_ida", "parent_description",
            "parent_item_id", "child_item_id", "child_ida", "child_description",
            "revision", "dt_effective_from", "dt_effective_to",
            "quantity", "scrap_factor", "yield_pct", "sequence",
            "is_alternate", "alternate_group", "is_optional",
            "cost_snapshot", "op_data", "change_reason", "dt_last_recalc",
        ]
        read_only_fields = _BASE_RO


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Catalog")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "name", "code", "currency", "dt_effective_start", "dt_effective_end",
            "is_active", "orgbase_id", "customer_orgbase_id",
            "manufacturer_orgbase_id", "rep_orgbase_id",
            "employee_orgbase_id", "connection_id", "metrics",
        ]
        read_only_fields = _BASE_RO


class OrgItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("OrgItem")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "item_id", "status", "orgbase_id", "catalog_id", "item_ida",
            "description", "availability_state",
            "quantity_minimum", "quantity_maximum", "inventory_frequency",
            "dt_last_checked", "dt_next_check", "data", "metrics",
        ]
        read_only_fields = _BASE_RO


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = _model("Warehouse")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "name", "location", "count", "priority", "code", "site_code",
            "is_active",
        ]
        read_only_fields = _BASE_RO


class ItemUsageSerializer(serializers.ModelSerializer):
    """Serializer for ItemUsage model (formerly 'Usage' which does not exist)."""
    class Meta:
        model = _model("ItemUsage")
        fields = [
            "id", "uuid", "dt_created", "dt_modified", "version",
            "is_active", "security_level", "is_deleted", "is_archived",
            "metadata", "refs", "prefs", "actions", "comments", "health_rating",
            "item_id", "status", "item_ida", "description",
            "year", "month", "metrics",
        ]
        read_only_fields = _BASE_RO


# Backward-compatible alias for code that imports UsageSerializer
UsageSerializer = ItemUsageSerializer


class InventoryReservationSerializer(serializers.ModelSerializer):
    """InventoryReservation does NOT extend BaseModel — limited system fields."""
    class Meta:
        model = _model("InventoryReservation")
        fields = [
            "id", "item_ida", "description", "item_id", "warehouse_id",
            "inventory_layer_id", "qty", "state", "dt_expires",
            "dt_committed", "dt_released", "context", "reason", "dt_modified",
        ]
        read_only_fields = ["id", "dt_modified"]


# NOTE: Flow model does not exist in the products app.
# Serializer removed to prevent import crash. Re-add when model is created.