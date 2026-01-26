from django.contrib import admin, messages
from django.db import models as dj_models
from .models import (
    Invoice, InvoiceLine,
    WorkOrderLine, Order, OrderLine, PurchaseOrder, PurchaseOrderLine,
    Proposal, ProposalLine, Requisition, RequisitionLine, WorkOrder,
    Project,
)
from .models.receipt import Receipt


# Scoped: other model admin registrations are deferred for now


class JSONBFieldsetMixin:
    """Group JSON-heavy fields at the end of the admin form."""

    readonly_auto_fields: tuple[str, ...] = ("id", "uuid", "dt_created", "dt_modified", "version")
    details_fieldset_title = "Record Details"
    jsonb_fieldset_title = "JSONB Payloads"

    def get_readonly_fields(self, request, obj=None):  # type: ignore[override]
        readonly = list(super().get_readonly_fields(request, obj))
        for field_name in self.readonly_auto_fields:
            if hasattr(self.model, field_name) and field_name not in readonly:
                readonly.append(field_name)
        return tuple(readonly)

    def _jsonb_field_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for field in self.model._meta.get_fields():
            if getattr(field, "auto_created", False):
                continue
            if isinstance(field, dj_models.JSONField):
                names.append(field.name)
        return tuple(sorted(dict.fromkeys(names)))

    def _non_jsonb_field_names(self) -> tuple[str, ...]:
        json_fields = set(self._jsonb_field_names())
        names: list[str] = []
        for field in self.model._meta.fields:
            if field.name in json_fields:
                continue
            names.append(field.name)
        return tuple(names)

    def get_fieldsets(self, request, obj=None):  # type: ignore[override]
        detail_fields = self._non_jsonb_field_names()
        json_fields = self._jsonb_field_names()
        fieldsets: list[tuple[str, dict]] = []
        if detail_fields:
            fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
        if json_fields:
            fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
        if fieldsets:
            return tuple(fieldsets)
        return super().get_fieldsets(request, obj)


##


##


##

@admin.register(Invoice)
class InvoiceAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created")
    search_fields = ("id",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "invoice_id", "status")
    list_filter = ("status",)


##


##


##

@admin.register(WorkOrderLine)
class WorkOrderLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "workorder_id", "status")
    list_filter = ("status",)

    # Admin bulk actions used in tests
    actions = [
        'action_start',
        'action_mark_rework',
        'action_mark_done',
    ]

    def action_start(self, request, queryset):
        """Transition planned -> in_progress for selected lines."""
        updated = 0
        for ln in queryset:
            prev = ln.status or 'planned'
            try:
                ln.status = 'in_progress'
                ln.save()
                updated += 1
            except Exception as e:
                messages.warning(request, f"Cannot start line {ln.pk} from {prev}: {e}")
        if updated:
            messages.info(request, f"Started {updated} workorder line(s)")
    action_start.short_description = "Start selected lines"

    def action_mark_rework(self, request, queryset):
        """Attempt to mark selected lines as rework. Planned -> rework is invalid and should remain planned."""
        changed = 0
        for ln in queryset:
            prev = ln.status or 'planned'
            try:
                ln.status = 'rework'
                ln.save()
                changed += 1
            except Exception:
                # Keep previous status; notify
                messages.warning(request, f"Cannot mark rework for line {ln.pk} from {prev}")
        if changed:
            messages.info(request, f"Reworked {changed} workorder line(s)")
    action_mark_rework.short_description = "Mark selected lines as rework"

    def action_mark_done(self, request, queryset):
        """Mark selected lines as done."""
        updated = 0
        for ln in queryset:
            try:
                ln.status = 'done'
                ln.save()
                updated += 1
            except Exception as e:
                messages.warning(request, f"Cannot mark done for line {ln.pk}: {e}")
        if updated:
            messages.info(request, f"Marked done: {updated} workorder line(s)")
    action_mark_done.short_description = "Mark selected lines as done"


@admin.register(Order)
class OrderAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(OrderLine)
class OrderLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "order_id", "status")
    list_filter = ("status",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(Project)
class ProjectAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "name", "is_active","intent", "status", "priority", "dt_created")
    list_filter = ("status", "priority")
    search_fields = ("id", "name", "intent", "slug")
    details_fieldset_title = "Project Details"

@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "purchaseorder_id", "status")
    list_filter = ("status",)


@admin.register(Proposal)
class ProposalAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(ProposalLine)
class ProposalLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "proposal_id", "status")
    list_filter = ("status",)


@admin.register(Requisition)
class RequisitionAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(RequisitionLine)
class RequisitionLineAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "requisition_id", "status")
    list_filter = ("status",)


@admin.register(Receipt)
class ReceiptAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_received")
    search_fields = ("id",)


@admin.register(WorkOrder)
class WorkOrderAdmin(JSONBFieldsetMixin, admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


##


##


##
