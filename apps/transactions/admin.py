from django.contrib import admin

from .models.line_variants import (
	Proposal, ProposalLine,
	Order, OrderLine,
	Invoice, InvoiceLine,
	Purchase, PurchaseLine,
	Workorder, WorkorderLine,
	Requisition, RequisitionLine,
)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "created_dt")
	search_fields = ("name",)


@admin.register(ProposalLine)
class ProposalLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status", "probability")
	list_filter = ("status",)
	search_fields = ("id",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "order_no", "created_dt")
	search_fields = ("order_no",)


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ("id", "invoice_no", "created_dt")
	search_fields = ("invoice_no",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
	list_display = ("id", "po_no", "created_dt")
	search_fields = ("po_no",)


@admin.register(PurchaseLine)
class PurchaseLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Workorder)
class WorkorderAdmin(admin.ModelAdmin):
	list_display = ("id", "work_no", "created_dt")
	search_fields = ("work_no",)


@admin.register(WorkorderLine)
class WorkorderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
	list_display = ("id", "req_no", "created_dt")
	search_fields = ("req_no",)


@admin.register(RequisitionLine)
class RequisitionLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)
