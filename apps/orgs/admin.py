from django.contrib import admin
from .models import OrgBase, Customer, Vendor, Rep, Employee, Manufacturer


@admin.register(OrgBase)
class OrgBaseAdmin(admin.ModelAdmin):
	list_display = ("id", "display_name", "org_type", "status", "is_active", "version")
	list_filter = ("org_type", "status", "is_active")
	search_fields = ("display_name", "domains", "contacts")
	readonly_fields = ("version", "dt_created", "dt_modified")
	fieldsets = (
		(None, {"fields": ("display_name", "org_type", "status", "is_active")}),
		("Aspects", {"fields": ("contacts", "locations", "domains", "phones", "emails", "relations", "financial", "docs", "connections", "data", "metrics", "gl_accounts"), 'classes': ('collapse',)}),
		("Versioning", {"fields": ("version", "dt_created", "dt_modified")}),
	)


def _proxy_admin(model, base: type[OrgBaseAdmin]):  # helper to clone config
	class ProxyAdmin(base):  # type: ignore
		def get_queryset(self, request):  # enforce proxy filter for admin
			qs = super().get_queryset(request)
			return qs.filter(org_type=model.objects.model.org_type if hasattr(model.objects.model, 'org_type') else model.__name__.replace('Org','').lower())
	return ProxyAdmin

for proxy_model in (Customer, Vendor, Rep, Employee, Manufacturer):
	try:
		admin.site.register(proxy_model, _proxy_admin(proxy_model, OrgBaseAdmin))
	except admin.sites.AlreadyRegistered:  # pragma: no cover
		pass

