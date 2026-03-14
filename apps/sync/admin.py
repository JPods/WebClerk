from django.contrib import admin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from common.admin_mixins import ScalarFirstFieldsetMixin

from .models.connection import Connection
from .models.bundle import Bundle
from .services.decisions import accept_email_verification, reject_bundle


@admin.register(Connection)
class ConnectionAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: action, comment, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version
	list_display = ("ida", "name", "status", "type", "action", "comment", "is_active", "dt_created")
	search_fields = ("name", "type")
	readonly_fields = ()


@admin.register(Bundle)
class BundleAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
	# Scalar fields: alert, direction, dt_created, dt_modified, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, size, status, uuid, version
	list_display = ("ida", "status", "alert", "direction", "duration", "health_rating", "is_active", "dt_created")
	search_fields = ("id", "status", "direction")
	actions = ("accept_selected", "reject_selected")

	def connection_link(self, obj):  # pragma: no cover - admin view
		return format_html("<a href='/admin/apps.sync/connection/{}/change/'>#{}</a>", obj.connection.id, obj.connection.id)

	connection_link.short_description = ".connection.id"

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
