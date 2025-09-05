from django.contrib import admin

from .models.line_variants import (
	Proposal, ProposalLine,
	SalesOrder, SalesOrderLine,
	Invoice, InvoiceLine,
	PurchaseOrder, PurchaseOrderLine,
	Workorder, WorkorderLine,
	Requisition, RequisitionLine,
)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "dt_created")
	search_fields = ("name",)


@admin.register(ProposalLine)
class ProposalLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status", "probability")
	list_filter = ("status",)
	search_fields = ("id",)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
	list_display = ("id", "order_no", "dt_created")
	search_fields = ("order_no",)


@admin.register(SalesOrderLine)
class SalesOrderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ("id", "invoice_no", "dt_created")
	search_fields = ("invoice_no",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
	list_display = ("id", "po_no", "dt_created")
	search_fields = ("po_no",)


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Workorder)
class WorkorderAdmin(admin.ModelAdmin):
	list_display = ("id", "work_no", "dt_created")
	search_fields = ("work_no",)


@admin.register(WorkorderLine)
class WorkorderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
	list_display = ("id", "req_no", "dt_created")
	search_fields = ("req_no",)


@admin.register(RequisitionLine)
class RequisitionLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)
