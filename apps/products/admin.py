from django.contrib import admin
from .models import (
    Item, ItemXRef, BillOfMaterial, Warehouse, InventoryLayer, SiteInventory, 
    InventoryMovement, OrgItem, Serial, SerialLog, Catalog, CatalogLine,
    InventoryCheck, InventoryCheckLine, DeliveryVisit, DeliveryLine, ItemUsage,
    Service, InventoryMetricsSnapshot, InventoryAdjustmentProcessorRun, Variant
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(ItemXRef)
class ItemXRefAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryLayer)
class InventoryLayerAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(SiteInventory)
class SiteInventoryAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(OrgItem)
class OrgItemAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Serial)
class SerialAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(SerialLog)
class SerialLogAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(CatalogLine)
class CatalogLineAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryCheck)
class InventoryCheckAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryCheckLine)
class InventoryCheckLineAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(DeliveryVisit)
class DeliveryVisitAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(DeliveryLine)
class DeliveryLineAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(ItemUsage)
class ItemUsageAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryMetricsSnapshot)
class InventoryMetricsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(InventoryAdjustmentProcessorRun)
class InventoryAdjustmentProcessorRunAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id",)
