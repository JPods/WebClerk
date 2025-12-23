from django.contrib import admin, messages
from .models import (
    Invoice, InvoiceLine,
    WorkOrderLine, SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine,
    Proposal, ProposalLine, Requisition, RequisitionLine, WorkOrder,
    Project,
)
from .models.purchase_receipt import PurchaseReceipt


# Scoped: other model admin registrations are deferred for now


##


##


##

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created")
    search_fields = ("id",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice_id", "status")
    list_filter = ("status",)


##


##


##

@admin.register(WorkOrderLine)
class WorkOrderLineAdmin(admin.ModelAdmin):
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


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(SalesOrderLine)
class SalesOrderLineAdmin(admin.ModelAdmin):
    list_display = ("id", "salesorder_id", "status")
    list_filter = ("status",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "intent", "status", "priority", "dt_created")
    list_filter = ("status", "priority")
    search_fields = ("id", "intent", "slug")

@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("id", "purchaseorder_id", "status")
    list_filter = ("status",)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(ProposalLine)
class ProposalLineAdmin(admin.ModelAdmin):
    list_display = ("id", "proposal_id", "status")
    list_filter = ("status",)


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(RequisitionLine)
class RequisitionLineAdmin(admin.ModelAdmin):
    list_display = ("id", "requisition_id", "status")
    list_filter = ("status",)


@admin.register(PurchaseReceipt)
class PurchaseReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_received")
    search_fields = ("id",)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "dt_created", "status")
    list_filter = ("status",)
    search_fields = ("id",)


##


##


##
