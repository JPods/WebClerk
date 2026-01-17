from django.contrib import admin
from .models import (
    Item, ItemXRef, BillOfMaterial, Warehouse, InventoryLayer, SiteInventory, 
    InventoryMovement, OrgItem, Serial, SerialLog, Catalog, CatalogLine,
    InventoryCheck, InventoryCheckLine, DeliveryVisit, DeliveryLine, ItemUsage,
    Service, InventoryMetricsSnapshot, InventoryAdjustmentProcessorRun, Variant
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "sku", "price_base", "cost_avg", "name", "description", "on_hand", "on_so", "on_po", "on_wo","on_p")

    @admin.display(description="price.base")
    def price_base(self, obj):
        if obj.price and isinstance(obj.price, dict):
            return obj.price.get("base")
        return None

    @admin.display(description="cost.avg")
    def cost_avg(self, obj):
        if obj.cost and isinstance(obj.cost, dict):
            return obj.cost.get("avg")
        return None

    @admin.display(description="on_hand")
    def on_hand(self, obj):
        if obj.quantity and isinstance(obj.quantity, dict):
            return obj.quantity.get("on_hand")
        return None
    @admin.display(description="on_so")
    def on_so(self, obj):
        if obj.quantity and isinstance(obj.quantity, dict):
            return obj.quantity.get("on_so")
        return None
    @admin.display(description="on_po")
    def on_po(self, obj):
        if obj.quantity and isinstance(obj.quantity, dict):
            return obj.quantity.get("on_po")
        return None
    @admin.display(description="on_wo")
    def on_wo(self, obj):
        if obj.quantity and isinstance(obj.quantity, dict):
            return obj.quantity.get("on_wo")
        return None
    @admin.display(description="on_p")
    def on_p(self, obj):
        if obj.quantity and isinstance(obj.quantity, dict):
            return obj.quantity.get("on_p")
        return None

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
