from django import forms
from django.contrib import admin
from .models import OrgBase, Customer, Vendor, Rep, Employee, Manufacturer


class OrgBaseAdminForm(forms.ModelForm):
    """Custom form to make JSON aspect fields optional."""
    
    class Meta:
        model = OrgBase
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all JSON aspect fields optional
        aspect_fields = [
            'contacts', 'locations', 'domains', 'phones', 'emails', 
            'relations', 'financial', 'docs', 'connections', 'data', 
            'metrics', 'gl_accounts'
        ]
        
        for field_name in aspect_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # Remove org_type field entirely for proxy models (it's auto-set in save_model)
        if hasattr(self.instance, '_meta') and self.instance._meta.proxy:
            self.fields.pop('org_type', None)
        elif 'org_type' in self.fields:
            # For OrgBase admin, keep org_type field but make it optional
            self.fields['org_type'].required = False


@admin.register(OrgBase)
class OrgBaseAdmin(admin.ModelAdmin):
    form = OrgBaseAdminForm
    list_display = ("id", "company", "org_type", "status", "is_active", "version")
    list_filter = ("org_type", "status", "is_active")
    search_fields = ("company", "domains", "contacts")
    readonly_fields = ("version", "dt_created", "dt_modified")
    fieldsets = (
        (None, {"fields": ("company", "org_type", "status", "is_active")}),
        ("Aspects", {"fields": ("contacts", "locations", "domains", "phones", "emails", "relations", "financial", "docs", "connections", "data", "metrics", "gl_accounts"), 'classes': ('collapse',)}),
        ("Versioning", {"fields": ("version", "dt_created", "dt_modified")}),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure org_type is set correctly based on the admin model being used."""
        # For proxy models, always set the correct org_type (override form data)
        if hasattr(obj, '_meta') and obj._meta.proxy:
            model_name = obj._meta.proxy_for_model.__name__
            if model_name == 'Customer':
                obj.org_type = 'customer'
            elif model_name == 'Vendor':
                obj.org_type = 'vendor'
            elif model_name == 'Rep':
                obj.org_type = 'rep'
            elif model_name == 'Employee':
                obj.org_type = 'employee'
            elif model_name == 'Manufacturer':
                obj.org_type = 'manufacturer'
        super().save_model(request, obj, form, change)


def _proxy_admin(model, base: type[OrgBaseAdmin]):  # helper to clone config
    class ProxyAdmin(base):  # type: ignore
        form = OrgBaseAdminForm  # Use the custom form for all proxy models
        
        def get_queryset(self, request):  # enforce proxy filter for admin
            qs = super().get_queryset(request)
            # Use the manager's _org_type attribute for proper filtering
            return qs.filter(org_type=model.objects._org_type)
    return ProxyAdmin

for proxy_model in (Customer, Vendor, Rep, Employee, Manufacturer):
    try:
        admin.site.register(proxy_model, _proxy_admin(proxy_model, OrgBaseAdmin))
    except admin.sites.AlreadyRegistered:  # pragma: no cover
        pass

