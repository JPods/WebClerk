from django.contrib import admin
from django.db import models as dj_models
try:
    from import_export.admin import ImportExportModelAdmin
except ImportError:
    ImportExportModelAdmin = admin.ModelAdmin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from common.admin_mixins import ScalarFirstFieldsetMixin  # noqa: F401 re-exported for app use
from .models import (
    Item, ItemXRef, BillOfMaterial, Warehouse, InventoryLayer, SiteInventory, 
    InventoryMovement, OrgItem, Serial, SerialLog, Catalog, CatalogLine,
    InventoryCheck, InventoryCheckLine, DeliveryVisit, DeliveryLine, ItemUsage,
    Service, InventoryMetricsSnapshot, InventoryAdjustmentProcessorRun, Variant
)
from .models.inventory_reservation import InventoryReservation
from .models.specification import Specification


@admin.register(Item)
class ItemAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, ImportExportModelAdmin):
    # Scalar fields: base_uom, description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version
    list_display = ("ida", "name", "sku", "description", "kind", "base_uom", "is_active", "dt_created")
    list_filter = ("kind", "is_active", "is_deleted")
    search_fields = ("ida", "name", "sku", "description")
    readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(ItemXRef)
class ItemXRefAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, external_sku, external_uuid, health_rating, is_active, is_archived, is_deleted, is_locked, is_preferred, security_level, source, source_id, source_model_name, source_name, status, uuid, version
    list_display = ("status", "external_sku", "external_uuid", "health_rating", "is_locked", "is_preferred", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: alternate_group, change_reason, child_description, child_ida, cost_snapshot, dt_created, dt_effective_from, dt_effective_to, dt_last_recalc, dt_modified, health_rating, is_active, is_alternate, is_archived, is_deleted, is_locked, is_optional, parent_description, parent_ida, quantity, revision, scrap_factor, security_level, sequence, uuid, version, yield_pct
    list_display = ("quantity", "child_ida", "child_description", "parent_ida", "parent_description", "cost_snapshot", "dt_effective_from", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Warehouse)
class WarehouseAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: code, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, name, priority, security_level, site_code, uuid, version
    list_display = ("name", "code", "health_rating", "is_locked", "priority", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryLayer)
class InventoryLayerAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, lot, security_level, serial_batch, source_doc_id, source_doc_type, status, uuid, version
    list_display = ("status", "health_rating", "is_locked", "lot", "security_level", "serial_batch", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(SiteInventory)
class SiteInventoryAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, security_level, site_code, status, uuid, version
    list_display = ("status", "health_rating", "is_locked", "security_level", "site_code", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryMovement)
class InventoryMovementAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, movement_type, quantity, reason, security_level, site_code, source_doc_id, source_doc_type, status, uuid, version
    list_display = ("status", "health_rating", "is_locked", "movement_type", "quantity", "reason", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(OrgItem)
class OrgItemAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: availability_state, description, dt_created, dt_last_checked, dt_modified, dt_next_check, health_rating, inventory_frequency, is_active, is_archived, is_deleted, is_locked, item_ida, quantity_maximum, quantity_minimum, security_level, status, uuid, version
    list_display = ("description", "status", "availability_state", "dt_last_checked", "dt_next_check", "health_rating", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Serial)
class SerialAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: description, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, item_ida, model_ida, qr_code, security_level, serial_ida, status, uuid, version
    list_display = ("description", "status", "health_rating", "is_locked", "item_ida", "model_ida", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(SerialLog)
class SerialLogAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: action, dt, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, security_level, uuid, version
    list_display = ("action", "dt", "health_rating", "is_locked", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Catalog)
class CatalogAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: code, currency, dt_created, dt_effective_end, dt_effective_start, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, name, security_level, uuid, version
    list_display = ("name", "code", "currency", "dt_effective_end", "dt_effective_start", "health_rating", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(CatalogLine)
class CatalogLineAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: discount_amount, discount_percent, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, price_unit, security_level, status, uuid, version
    list_display = ("status", "discount_amount", "discount_percent", "health_rating", "is_locked", "price_unit", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryCheck)
class InventoryCheckAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, dt_performed, health_rating, is_active, is_archived, is_deleted, is_locked, notes, security_level, status, uuid, version
    list_display = ("status", "dt_performed", "health_rating", "is_locked", "notes", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryCheckLine)
class InventoryCheckLineAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: auto_flag, counted_qty, description, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, item_ida, prior_qty, security_level, uuid, variance_qty, version
    list_display = ("description", "auto_flag", "counted_qty", "health_rating", "is_locked", "item_ida", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(DeliveryVisit)
class DeliveryVisitAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_arrived, dt_completed, dt_created, dt_modified, dt_scheduled, health_rating, is_active, is_archived, is_deleted, is_locked, notes, security_level, status, uuid, version
    list_display = ("status", "dt_arrived", "dt_completed", "dt_scheduled", "health_rating", "is_locked", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(DeliveryLine)
class DeliveryLineAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: delivered_qty, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, loaded_qty, planned_qty, security_level, skipped_reason, status, uuid, version
    list_display = ("status", "delivered_qty", "health_rating", "is_locked", "loaded_qty", "planned_qty", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(ItemUsage)
class ItemUsageAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: description, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, item_ida, month, security_level, status, uuid, version, year
    list_display = ("description", "status", "health_rating", "is_locked", "item_ida", "month", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(Service)
class ServiceAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: category, default_duration_minutes, description, display, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, purpose, row_version, security_level, status, uuid, version
    list_display = ("ida", "description", "status", "category", "default_duration_minutes", "display", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("ida", "description")


@admin.register(InventoryMetricsSnapshot)
class InventoryMetricsSnapshotAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, security_level, uuid, version
    list_display = ("health_rating", "is_locked", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ()


@admin.register(InventoryAdjustmentProcessorRun)
class InventoryAdjustmentProcessorRunAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: applied, attempted, canceled, dry_run, dt_created, dt_finished, dt_modified, dt_started, duration_s, health_rating, insufficient, is_active, is_archived, is_deleted, is_locked, reserved_conflict_skipped, run_type, security_level, skipped_locked, stack_id, still_locked, uuid, version
    list_display = ("applied", "attempted", "canceled", "dry_run", "dt_finished", "dt_started", "is_active", "dt_created")
    list_filter = ("run_type", "dry_run", "is_active")
    search_fields = ("run_type",)


@admin.register(Variant)
class VariantAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: canonical_key, description, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, item_ida, security_level, set_uuid, uuid, variant_uuid, version
    list_display = ("description", "canonical_key", "health_rating", "is_locked", "item_ida", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("item_ida", "canonical_key", "description")


@admin.register(InventoryReservation)
class InventoryReservationAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    # Scalar fields: description, dt_committed, dt_expires, dt_modified, dt_released, item_ida, qty, reason, state
    list_display = ("description", "dt_committed", "dt_expires", "dt_released", "item_ida", "qty")
    list_filter = ("state", "warehouse")
    search_fields = ("item_ida", "description", "reason")


@admin.register(Specification)
class SpecificationAdmin(SchemaLabelsAdminMixin, ScalarFirstFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: description, description_long, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, security_level, status, unit, uuid, version
    list_display = ("ida", "name", "description", "status", "description_long", "health_rating", "is_active", "dt_created")
    list_filter = ("status", "is_active", "unit")
    search_fields = ("name", "description", "unit", "ida")
