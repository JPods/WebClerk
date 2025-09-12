from django.contrib import admin, messages

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
	list_display = ("id", "work_no", "status", "dt_created")
	list_filter = ("status",)
	search_fields = ("work_no",)

	# Quick status transitions
	actions = [
		"action_release",
		"action_start",
		"action_hold",
		"action_complete",
		"action_cancel",
	]

	def _bulk_status(self, request, queryset, status: str):
		success, failed = 0, 0
		for obj in queryset:
			old = obj.status
			obj.status = status
			try:
				obj.save()
				success += 1
			except Exception as e:  # ValidationError or others
				failed += 1
				self.message_user(request, f"{obj.work_no or obj.pk}: {e}", level=messages.ERROR)
		if success:
			self.message_user(request, f"Updated {success} work order(s) to '{status}'.")
		if failed:
			self.message_user(request, f"{failed} work order(s) failed transition to '{status}'.", level=messages.WARNING)

	def action_release(self, request, queryset):
		self._bulk_status(request, queryset, "released")
	action_release.short_description = "Mark selected work orders as Released"

	def action_start(self, request, queryset):
		self._bulk_status(request, queryset, "in_progress")
	action_start.short_description = "Mark selected work orders as In Progress"

	def action_hold(self, request, queryset):
		self._bulk_status(request, queryset, "hold")
	action_hold.short_description = "Place selected work orders On Hold"

	def action_complete(self, request, queryset):
		self._bulk_status(request, queryset, "complete")
	action_complete.short_description = "Mark selected work orders as Complete"

	def action_cancel(self, request, queryset):
		self._bulk_status(request, queryset, "canceled")
	action_cancel.short_description = "Cancel selected work orders"


@admin.register(WorkorderLine)
class WorkorderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)

	# Bulk actions for common transitions; each routes through save() for validation
	actions = [
		"action_start",
		"action_mark_done",
		"action_skip",
		"action_mark_rework",
	]

	def _bulk_status(self, request, queryset, status: str):
		success, failed = 0, 0
		for obj in queryset:
			old = obj.status
			obj.status = status
			try:
				obj.save()
				success += 1
			except Exception as e:
				failed += 1
				self.message_user(request, f"Line {obj.pk} ({old} -> {status}): {e}", level=messages.ERROR)
		if success:
			self.message_user(request, f"Updated {success} line(s) to '{status}'.")
		if failed:
			self.message_user(request, f"{failed} line(s) failed transition to '{status}'.", level=messages.WARNING)

	def action_start(self, request, queryset):
		self._bulk_status(request, queryset, "in_progress")
	action_start.short_description = "Mark selected lines as In Progress"

	def action_mark_done(self, request, queryset):
		self._bulk_status(request, queryset, "done")
	action_mark_done.short_description = "Mark selected lines as Done"

	def action_skip(self, request, queryset):
		self._bulk_status(request, queryset, "skipped")
	action_skip.short_description = "Skip selected lines"

	def action_mark_rework(self, request, queryset):
		self._bulk_status(request, queryset, "rework")
	action_mark_rework.short_description = "Mark selected lines as Rework"


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
	list_display = ("id", "req_no", "dt_created")
	search_fields = ("req_no",)


@admin.register(RequisitionLine)
class RequisitionLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_ref_id", "status")
	list_filter = ("status",)
