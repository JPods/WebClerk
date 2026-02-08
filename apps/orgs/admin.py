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
            'contacts', 'addresses', 'domains', 'phones', 'emails', 
            'relations', 'financial', 'docs', 'connections', 'data', 
            'metrics', 'gl_accounts'
        ]
        
        for field_name in aspect_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # For proxy models, make org_type field hidden but still present
        if hasattr(self.instance, '_meta') and self.instance._meta.proxy:
            if 'org_type' in self.fields:
                self.fields['org_type'].widget = forms.HiddenInput()
        elif 'org_type' in self.fields:
            # For OrgBase admin, keep org_type field but make it optional
            self.fields['org_type'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        print(f"Form cleaned_data: {cleaned_data}")
        return cleaned_data


@admin.register(OrgBase)
class OrgBaseAdmin(admin.ModelAdmin):
    form = OrgBaseAdminForm
    # Show `company` (alias property) in list display; searches still operate against DB column `display_name`.
    list_display = ("id", "company", "org_type", "status", "is_active", "version")
    list_filter = ("org_type", "status", "is_active")
    search_fields = ("display_name", "domains", "contacts")
    readonly_fields = ("version", "dt_created", "dt_modified")
    fieldsets = (
        (None, {"fields": ("display_name", "org_type", "status", "is_active")}),
        ("Aspects", {"fields": ("contacts", "addresses", "domains", "phones", "emails", "relations", "financial", "docs", "connections", "data", "metrics", "gl_accounts"), 'classes': ('collapse',)}),
        ("Versioning", {"fields": ("version", "dt_created", "dt_modified")}),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure org_type is set correctly based on the admin model being used."""
        # Log for debugging
        print(f"save_model called: {obj.__class__.__name__}, proxy={getattr(obj._meta, 'proxy', False)}, change={change}")
        
        # For proxy models, always set the correct org_type (override form data)
        if getattr(obj._meta, 'proxy', False):
            model_name = obj.__class__.__name__
            print(f"Detected proxy model: {model_name}")
            if model_name == 'Customer':
                obj.org_type = 'customer'
            elif model_name == 'Vendor':
                obj.org_type = 'vendor'
            elif model_name == 'Rep':
                obj.org_type = 'rep'
            elif model_name == 'Employee':
                obj.org_type = 'employee'
                print("Setting org_type to 'employee'")
            elif model_name == 'Manufacturer':
                obj.org_type = 'manufacturer'
        
        try:
            super().save_model(request, obj, form, change)
            print(f"Successfully saved {obj.__class__.__name__} with ID {obj.id}")
        except Exception as e:
            print(f"Error saving {obj.__class__.__name__}: {e}")
            raise


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

