from django.contrib import admin, messages

from .models import (
    Invoice, InvoiceLine,
	WorkorderLine,
)


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
	list_display = ("id", "parent_id", "status")
	list_filter = ("status",)


##


##


##


@admin.register(WorkorderLine)
class WorkorderLineAdmin(admin.ModelAdmin):
	list_display = ("id", "parent_id", "status")
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


##


##


##
