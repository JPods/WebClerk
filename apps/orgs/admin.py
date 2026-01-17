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
        
        # Make all JSON/object fields optional
        json_fields = [
            # OrgBase aspects
            'contacts', 'locations', 'domains', 'phones', 'emails', 
            'relations', 'financial', 'docs', 'connections', 'data', 
            'metrics', 'gl_accounts',
            # BaseModel mixins
            'metadata', 'refs', 'prefs', 'comments', 'actions',
        ]
        
        for field_name in json_fields:
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
        return cleaned_data


@admin.register(OrgBase)
class OrgBaseAdmin(admin.ModelAdmin):
    form = OrgBaseAdminForm
    # Show `company` (alias property) in list display; searches still operate against DB column `display_name`.
    list_display = ("id", "company", "org_type", "status", "is_active", "version")
    list_filter = ("org_type", "status", "is_active", "is_deleted", "is_archived")
    search_fields = ("display_name", "ida")
    readonly_fields = ("id", "uuid", "ida", "version", "dt_created", "dt_modified", "health_rating")
    
    # Fieldsets organized: Scalar fields (alphabetically), then Object fields (alphabetically)
    fieldsets = (
        ("Identity & Status (Scalars)", {
            "fields": (
                # Scalars alphabetically
                "display_name",
                "dt_created",
                "dt_modified",
                "health_rating",
                "id",
                "ida",
                "is_active",
                "is_archived",
                "is_deleted",
                "org_type",
                "security_level",
                "status",
                "uuid",
                "version",
            )
        }),
        ("OrgBase Aspects (Objects)", {
            "fields": (
                # OrgBase JSON fields alphabetically
                "connections",
                "contacts",
                "data",
                "docs",
                "domains",
                "emails",
                "financial",
                "gl_accounts",
                "locations",
                "metrics",
                "phones",
                "relations",
            ),
            "classes": ("collapse",),
        }),
        ("BaseModel Mixins (Objects)", {
            "fields": (
                # BaseModel mixin JSON fields alphabetically
                "actions",
                "comments",
                "metadata",
                "prefs",
                "refs",
            ),
            "classes": ("collapse",),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure org_type is set correctly based on the admin model being used."""
        # For proxy models, always set the correct org_type (override form data)
        if getattr(obj._meta, 'proxy', False):
            model_name = obj.__class__.__name__
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

