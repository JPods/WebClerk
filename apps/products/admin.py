from django.contrib import admin
from django.db import models as dj_models
from .models import (
    Item, ItemXRef, BillOfMaterial, Warehouse, InventoryLayer, SiteInventory, 
    InventoryMovement, OrgItem, Serial, SerialLog, Catalog, CatalogLine,
    InventoryCheck, InventoryCheckLine, DeliveryVisit, DeliveryLine, ItemUsage,
    Service, InventoryMetricsSnapshot, InventoryAdjustmentProcessorRun, Variant
)


class ScalarFirstFieldsetMixin:
    """Dynamically build fieldsets: scalar fields alphabetically, then JSON/object fields."""
    
    readonly_auto_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
    scalar_fieldset_title = "Scalar Fields"
    object_fieldset_title = "Object/JSON Fields"
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        for field_name in self.readonly_auto_fields:
            if hasattr(self.model, field_name) and field_name not in readonly:
                readonly.append(field_name)
        return tuple(readonly)
    
    def _get_scalar_fields(self):
        """Get scalar (non-JSON, non-relation) fields alphabetically."""
        names = []
        for field in self.model._meta.fields:
            if isinstance(field, dj_models.JSONField):
                continue
            if isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField, dj_models.ManyToManyField)):
                continue
            names.append(field.name)
        return tuple(sorted(names))
    
    def _get_object_fields(self):
        """Get JSON and relation fields alphabetically."""
        names = []
        for field in self.model._meta.fields:
            if isinstance(field, dj_models.JSONField):
                names.append(field.name)
            elif isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField)):
                names.append(field.name)
        return tuple(sorted(names))
    
    def get_fieldsets(self, request, obj=None):
        scalar_fields = self._get_scalar_fields()
        object_fields = self._get_object_fields()
        fieldsets = []
        if scalar_fields:
            fieldsets.append((self.scalar_fieldset_title, {"fields": scalar_fields}))
        if object_fields:
            fieldsets.append((self.object_fieldset_title, {"fields": object_fields, "classes": ("collapse",)}))
        if fieldsets:
            return tuple(fieldsets)
        return super().get_fieldsets(request, obj)


@admin.register(Item)
class ItemAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "name", "sku", "description", "kind", "on_hand", "allocated", "available", "is_active", "dt_created")
    list_filter = ("kind", "is_active", "is_deleted")
    search_fields = ("ida", "name", "sku", "description")
    readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(ItemXRef)
class ItemXRefAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Warehouse)
class WarehouseAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryLayer)
class InventoryLayerAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(SiteInventory)
class SiteInventoryAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(OrgItem)
class OrgItemAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Serial)
class SerialAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(SerialLog)
class SerialLogAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Catalog)
class CatalogAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(CatalogLine)
class CatalogLineAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryCheck)
class InventoryCheckAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryCheckLine)
class InventoryCheckLineAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(DeliveryVisit)
class DeliveryVisitAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(DeliveryLine)
class DeliveryLineAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(ItemUsage)
class ItemUsageAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Service)
class ServiceAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "ida", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryMetricsSnapshot)
class InventoryMetricsSnapshotAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ()


@admin.register(InventoryAdjustmentProcessorRun)
class InventoryAdjustmentProcessorRunAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "run_type", "dry_run", "dt_started", "dt_finished", "applied", "attempted", "is_active", "dt_created")
    list_filter = ("run_type", "dry_run", "is_active")
    search_fields = ("run_type",)


@admin.register(Variant)
class VariantAdmin(ScalarFirstFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "item_ida", "canonical_key", "description", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("item_ida", "canonical_key", "description")
