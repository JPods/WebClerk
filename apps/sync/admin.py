from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models.connection import Connection
from .models.bundle import Bundle
from .services.decisions import accept_email_verification, reject_bundle


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "type", "status")
	search_fields = ("name", "type")
	readonly_fields = ()


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
	list_display = ("id", "connection_link", "direction", "status", "duration")
	search_fields = ("id", "status", "direction")
	actions = ("accept_selected", "reject_selected")

	def connection_link(self, obj):  # pragma: no cover - admin view
		return format_html("<a href='/admin/apps.sync/connection/{}/change/'>#{}</a>", obj.connection_id.id, obj.connection_id.id)

	connection_link.short_description = "Connection"

	def accept_selected(self, request, queryset):  # pragma: no cover - admin action
		count = 0
		for ex in queryset:
			res = accept_email_verification(ex.id, actor_id=getattr(request.user, "id", 0))
			if res.get("ok"):
				count += 1
		self.message_user(request, f"Accepted {count} bundle(s)")

	def reject_selected(self, request, queryset):  # pragma: no cover - admin action
		count = 0
		for ex in queryset:
			res = reject_bundle(ex.id, reason="admin_reject", actor_id=getattr(request.user, "id", 0))
			if res.get("ok"):
				count += 1
		self.message_user(request, f"Rejected {count} bundle(s)")
