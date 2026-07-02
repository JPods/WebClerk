from django import forms
from django.contrib import admin
from django.contrib import messages
try:
    from import_export.admin import ImportExportModelAdmin
except ImportError:
    ImportExportModelAdmin = admin.ModelAdmin
import logging
from common.admin_schema_labels import SchemaLabelsAdminMixin
from .models import OrgBase, Customer, Vendor, Rep, Employee, Manufacturer
from .services.primary_org import get_primary_org_id, set_primary_org

logger = logging.getLogger(__name__)


class OrgBaseAdminForm(forms.ModelForm):
    """Custom form to make JSON aspect fields optional."""
    
    class Meta:
        model = OrgBase
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all JSON aspect fields optional (alphabetical)
        aspect_fields = [
            'actions', 'addresses', 'comments', 'connections', 'contacts', 'data',
            'docs', 'domains', 'emails', 'financial', 'gl_accounts', 'metadata',
            'metrics', 'phones', 'prefs', 'refs', 'relations', 'relationship_stats', 'stats',
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
        logger.debug("OrgBaseAdminForm.clean: %s", list(cleaned_data.keys()))
        return cleaned_data


@admin.register(OrgBase)
class OrgBaseAdmin(SchemaLabelsAdminMixin, ImportExportModelAdmin or admin.ModelAdmin):
    form = OrgBaseAdminForm
    # Show `company` (alias property) in list display; searches still operate against DB column `display_name`.
    # Scalar fields: address_full, address_id, attention, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, uuid, version
    list_display = ("ida", "display_name", "status", "email", "phone", "address_full", "is_active", "dt_created")
    list_filter = ("org_type", "status", "is_active", "is_deleted", "is_archived")
    search_fields = ("display_name", "domains", "contacts", "email", "phone")
    readonly_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
    raw_id_fields = ("contact", "terms_fk")
    actions = ("mark_as_primary_organization",)
    
    # Scalar fields alphabetical, then JSONB fields alphabetical
    fieldsets = (
        ("Scalar fields", {"fields": (
            "address_full", "address_id", "attention",
            "contact", "display_name", "domain", "domain_id",
            "email", "email_id", "health_rating",
            "is_active", "is_archived", "is_deleted",
            "org_type", "phone", "phone_id", "price_level",
            "security_level", "status", "terms", "terms_fk",
        )}),
        ("JSONB fields", {
            "fields": (
                "actions", "addresses", "comments", "connections", "contacts",
                "data", "docs", "domains", "emails", "financial",
                "gl_accounts", "metadata", "metrics", "phones", "prefs",
                "refs", "relations", "relationship_stats", "stats",
            ),
            "classes": ("collapse",),
        }),
        ("System (read-only)", {
            "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
            "classes": ("collapse",),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure org_type is set correctly based on the admin model being used."""
        # For proxy models, always set the correct org_type (override form data)
        if getattr(obj._meta, 'proxy', False):
            model_name = obj.__class__.__name__
            logger.debug("save_model: proxy model %s", model_name)
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
        
        try:
            super().save_model(request, obj, form, change)
            logger.info("Saved %s id=%s", obj.__class__.__name__, obj.id)
        except Exception as e:
            logger.error("Error saving %s: %s", obj.__class__.__name__, e)
            raise

    @admin.display(description=".primary_org")
    def primary_org_badge(self, obj):
        primary_org_id = get_primary_org_id()
        return "PRIMARY" if primary_org_id and obj.pk == primary_org_id else ""

    @admin.action(description="Mark selected org as primary organization")
    def mark_as_primary_organization(self, request, queryset):
        if not getattr(request.user, "is_superuser", False):
            self.message_user(request, "Only superusers may change the primary organization.", level=messages.ERROR)
            return

        selected = list(queryset[:2])
        if len(selected) != 1:
            self.message_user(request, "Select exactly one org record to mark as primary.", level=messages.WARNING)
            return

        org = selected[0]
        try:
            setting = set_primary_org(org, actor=request.user)
        except Exception as exc:
            self.message_user(request, f"Failed to set primary organization: {exc}", level=messages.ERROR)
            return

        self.message_user(
            request,
            f"Primary organization set to org id={org.pk} using Setting id={setting.pk}.",
            level=messages.SUCCESS,
        )


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

