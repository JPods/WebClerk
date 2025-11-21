from django.contrib import admin
from .models import (
    Item, ItemXRef, BillOfMaterial, Warehouse, InventoryLayer, SiteInventory, 
    InventoryMovement, OrgItem, Serial, SerialLog, Catalog, CatalogLine,
    InventoryCheck, InventoryCheckLine, DeliveryVisit, DeliveryLine, ItemUsage,
    Service, InventoryMetricsSnapshot, InventoryAdjustmentProcessorRun, Variant
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "sku", "name", "item_type", "is_active")
    list_filter = ("item_type", "is_active")
    search_fields = ("sku", "name")


@admin.register(ItemXRef)
class ItemXRefAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "external_id", "external_system")
    search_fields = ("item__sku", "external_id")


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "version", "is_active")
    list_filter = ("is_active",)
    search_fields = ("item__sku",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(InventoryLayer)
class InventoryLayerAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "warehouse", "quantity", "cost_per_unit")
    list_filter = ("warehouse",)
    search_fields = ("item__sku",)


@admin.register(SiteInventory)
class SiteInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "warehouse", "available_quantity", "reserved_quantity")
    list_filter = ("warehouse",)
    search_fields = ("item__sku",)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "from_warehouse", "to_warehouse", "quantity", "movement_type")
    list_filter = ("movement_type", "from_warehouse", "to_warehouse")
    search_fields = ("item__sku",)


@admin.register(OrgItem)
class OrgItemAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "item", "preferred_vendor")
    search_fields = ("org__company", "item__sku")


@admin.register(Serial)
class SerialAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "serial_number", "status")
    list_filter = ("status",)
    search_fields = ("item__sku", "serial_number")


@admin.register(SerialLog)
class SerialLogAdmin(admin.ModelAdmin):
    list_display = ("id", "serial", "action", "dt_created")
    list_filter = ("action",)
    search_fields = ("serial__serial_number",)


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name",)


@admin.register(CatalogLine)
class CatalogLineAdmin(admin.ModelAdmin):
    list_display = ("id", "catalog", "item", "price")
    search_fields = ("catalog__name", "item__sku")


@admin.register(InventoryCheck)
class InventoryCheckAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "status", "dt_created")
    list_filter = ("status", "warehouse")
    search_fields = ("warehouse__name",)


@admin.register(InventoryCheckLine)
class InventoryCheckLineAdmin(admin.ModelAdmin):
    list_display = ("id", "check", "item", "expected_qty", "actual_qty")
    search_fields = ("check__warehouse__name", "item__sku")


@admin.register(DeliveryVisit)
class DeliveryVisitAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery_date", "status", "driver")
    list_filter = ("status",)
    search_fields = ("driver",)


@admin.register(DeliveryLine)
class DeliveryLineAdmin(admin.ModelAdmin):
    list_display = ("id", "visit", "item", "quantity_delivered")
    search_fields = ("visit__driver", "item__sku")


@admin.register(ItemUsage)
class ItemUsageAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "quantity", "usage_date", "reference")
    search_fields = ("item__sku", "reference")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "service_type", "is_active")
    list_filter = ("service_type", "is_active")
    search_fields = ("name",)


@admin.register(InventoryMetricsSnapshot)
class InventoryMetricsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "snapshot_date", "total_items", "total_value")
    search_fields = ("snapshot_date",)


@admin.register(InventoryAdjustmentProcessorRun)
class InventoryAdjustmentProcessorRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_run", "status", "records_processed")
    list_filter = ("status",)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_item", "variant_sku", "attributes")
    search_fields = ("parent_item__sku", "variant_sku")
