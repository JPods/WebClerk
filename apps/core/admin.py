from types import MethodType
from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin.helpers import ActionForm
from django.contrib.admin.utils import display_for_field
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

try:
    from django_json_widget.widgets import JSONEditorWidget
except Exception:
    JSONEditorWidget = None

from apps.transactions.models import Project
from common.admin_schema_labels import SchemaLabelsAdminMixin
from common.admin_mixins import ScalarFirstFieldsetMixin
from .models import (
    Contact, Action, Setting, Template, Pending, SoftDeleteLedger, Notification, Report,
    RoleConfig, ModelRoleConfig, ModelLinkConfig, UserProfile,
)


class ContactAdminForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        refs_field = self.fields.get("refs")
        if not refs_field:
            return

        if JSONEditorWidget is not None:
            refs_field.widget = JSONEditorWidget(width="100%", height="480px")
        else:
            refs_field.widget = forms.Textarea(
                attrs={
                    "rows": 24,
                    "style": "font-family: ui-monospace, SFMono-Regular, Menlo, monospace;",
                }
            )


@admin.register(Contact)
class ContactAdmin(SchemaLabelsAdminMixin, BaseUserAdmin):
    """Admin interface for Contact model (custom user model)."""
    form = ContactAdminForm
    scalar_fields = (
        'id',
        'ida',
        'attention',
        'role',
        'email',
        'name_first',
        'name_last',
        'company',
        'is_staff',
        'is_superuser',
        'customer',
        'rep',
        'employee',
        'manufacturer',
        'vendor',
        'other_id',
        'security_level',
        'title',
        'department',
    )
    # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
    list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'name_first', 'name_last', 'company')
    readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
    raw_id_fields = ('customer', 'vendor', 'manufacturer', 'rep', 'employee')
    ordering = ('name_last', 'name_first')
    object_fields = (
        'actions',
        'comments',
        'groups',
        'metadata',
        'prefs',
        'refs',
        'user_permissions',
    )
    detail_fields = scalar_fields + object_fields
    
    # Specify the fields to be used in displaying the User model
    # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal info', {
            'classes': ('wide',),
            'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
        }),
        ('Company info', {
            'classes': ('wide',),
            'fields': (
                'company',
                'title',
                'department',
                'employee',
                'customer',
                'vendor',
                'manufacturer',
                'rep',
                'other_id',
            ),
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('role', 'is_active', 'is_staff'),
        }),
    )
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Scalar fields', {'fields': (
            'address_full', 'address_id', 'attention', 'company',
            'customer', 'department', 'domain', 'domain_id',
            'email_id', 'employee', 'health_rating',
            'is_active', 'is_archived', 'is_deleted', 'is_staff', 'is_superuser',
            'manufacturer', 'name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix',
            'other_id', 'phone', 'phone_id',
            'rep', 'role', 'security_level', 'title', 'vendor',
        )}),
        ('JSONB fields', {
            'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('System (read-only)', {
            'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
            'classes': ('collapse',),
        }),
    )
    
    # Override the get_fieldsets method to use our custom fieldsets
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)
    
    # Override get_form to prevent issues with username field
    def get_form(self, request, obj=None, **kwargs):
        # Remove username from kwargs if it's passed by parent
        kwargs.pop('username', None)
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        # Provide exhaustive field listing for detail views without disturbing add/change layouts.
        if obj:
            return self.detail_fields
        return super().get_fields(request, obj)


@admin.register(Action)
class ActionAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Action model."""
    # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
    list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
    list_filter = ('kanban_column', 'status', 'priority')
    search_fields = ('project_id', 'action')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    # Keep scalar then object fields alphabetical for detail view coherence.
    scalar_fields = (
        'parent_action',
        'burndown',
        'difficulty',
        'dt_completed',
        'dt_created',
        'dt_expected',
        'dt_modified',
        'dt_start',
        'dt_updated',
        'duration',
        'health_rating',
        'ida',
        'is_active',
        'is_archived',
        'is_deleted',
        'kanban_column',
        'linkage',
        'percent_complete',
        'priority',
        'project_id',
        'project_name',
        'sequence',
        'security_level',
        'status',
        'uuid',
        'version',
    )
    object_fields = (
        'action',
        'actions',
        'assigned_to',
        'comments',
        'completed_by',
        'created_by',
        'description',
        'end_by',
        'expected_by',
        'languages',
        'metadata',
        'prefs',
        'project_metadata',
        'refs',
        'start_by',
        'updated_by',
    )
    fields = scalar_fields + object_fields
    actions = ['assign_project_id', 'delete_selected']

    class AssignProjectIdActionForm(ActionForm):
        # Keep optional so other actions (like delete_selected) don't fail validation
        project_id = forms.CharField(required=False, label='Project ID')

    action_form = AssignProjectIdActionForm

    @admin.display(description='assigned_to')
    def assigned_to_names(self, obj):
        """Render names from assigned_to JSON for changelist readability."""
        assigned = obj.assigned_to
        if not assigned:
            return '-'

        def pick_name(entry):
            if isinstance(entry, str):
                return entry
            if not isinstance(entry, dict):
                return None
            return (
                entry.get('name')
                or entry.get('full_name')
                or entry.get('display_name')
                or entry.get('title')
                or entry.get('email')
                or entry.get('ida')
            )

        if isinstance(assigned, dict):
            return pick_name(assigned) or '-'

        if isinstance(assigned, list):
            names = [pick_name(entry) for entry in assigned]
            names = [name for name in names if name]
            return ', '.join(names) if names else '-'

        return str(assigned)

    @admin.display(description='description.en')
    def description_en(self, obj):
        desc = obj.description
        if isinstance(desc, dict):
            return desc.get('en') or '-'
        return desc or '-'
    
    def get_action_title(self, obj):
        task_dict = obj.action or {}
        return task_dict.get('en') or task_dict.get('bn') or task_dict.get('ar') or 'Untitled'
    get_action_title.short_description = '.en'

    @admin.action(description='Assign project ID to selected actions')
    def assign_project_id(self, request, queryset):
        project_id_raw = request.POST.get('project_id')
        if not project_id_raw:
            messages.error(request, 'Project ID is required to update selected actions.')
            return
        try:
            project_id_clean = int(project_id_raw)
        except (TypeError, ValueError):
            messages.error(request, f'Invalid project ID "{project_id_raw}" provided.')
            return
        try:
            project = Project.objects.get(id=project_id_clean)
        except Project.DoesNotExist:
            messages.error(request, f'No project found with ID "{project_id_clean}".')
            return
        project_name = project.slug or project.intent or str(project.id)
        updated = queryset.update(project_id=project.id, project_name=project_name)
        messages.success(request, f'Assigned project ID {project.id} ({project_name}) to {updated} action(s).')


@admin.register(Setting)
class SettingAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Setting model."""
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, parent_model, purpose, role, security_level, uuid, version
    list_display = ("ida", "name", "health_rating", "is_locked", "parent_model", "purpose", "is_active", "dt_created")
    list_filter = ('purpose', 'role')
    search_fields = ('name', 'purpose', 'parent_model')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(Template)
class TemplateAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Template model."""
    # Scalar fields: dt_created, dt_modified, dt_processed, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, uuid, version
    list_display = ("ida", "name", "dt_processed", "health_rating", "is_locked", "purpose", "is_active", "dt_created")
    list_filter = ('purpose',)
    search_fields = ('name', 'purpose')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(Pending)
class PendingAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Pending model."""
    # Scalar fields: dt_created, dt_modified, dt_processed, ida, is_active, model_name, name, purpose, record_id, security_level, uuid, version
    list_display = ("ida", "name", "dt_processed", "model_name", "purpose", "record_id", "on_hand", "on_p", "on_so", "on_in", "on_po", "is_active", "dt_created")
    list_filter = ('model_name', 'purpose')
    search_fields = ('model_name', 'record_id', 'name')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')

    def _data_field(self, obj, key):
        val = (obj.config or {}).get(key)
        return val if val is not None else '-'

    @admin.display(description='.on_hand')
    def on_hand(self, obj):
        return self._data_field(obj, 'on_hand')

    @admin.display(description='.on_p')
    def on_p(self, obj):
        return self._data_field(obj, 'on_p')

    @admin.display(description='.on_so')
    def on_so(self, obj):
        return self._data_field(obj, 'on_so')

    @admin.display(description='.on_in')
    def on_in(self, obj):
        return self._data_field(obj, 'on_in')

    @admin.display(description='.on_po')
    def on_po(self, obj):
        return self._data_field(obj, 'on_po')


@admin.register(SoftDeleteLedger)
class SoftDeleteLedgerAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for SoftDeleteLedger model."""
    # Scalar fields: dt_purge, object_id, target
    list_display = ("dt_purge", "object_id", "target")
    list_filter = ('content_type', 'dt_purge')
    search_fields = ('content_type__model', 'object_id')
    readonly_fields = ('dt_created',)


@admin.register(Notification)
class NotificationAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Notification model."""
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, purpose, record_id, security_level, uuid, version
    list_display = ("ida", "name", "health_rating", "is_locked", "model_name", "purpose", "is_active", "dt_created")
    list_filter = ('purpose', 'model_name', 'is_active')
    search_fields = ('name', 'purpose', 'model_name', 'record_id')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(Report)
class ReportAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Report model."""
    # Scalar fields: category, description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, output_type, purpose, record_id, role_required, security_level, sort_order, uuid, version
    list_display = ("ida", "name", "description", "category", "health_rating", "is_locked", "is_active", "dt_created")
    list_filter = ('purpose', 'model_name', 'is_active')
    search_fields = ('name', 'purpose', 'model_name', 'record_id')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


# =============================================================================
# RBAC Admin
# =============================================================================

@admin.register(RoleConfig)
class RoleConfigAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Role configurations."""
    # Scalar fields: description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_portal, parent_role, role, security_level, uuid, version
    list_display = ("ida", "description", "health_rating", "is_locked", "is_portal", "parent_role", "is_active", "dt_created")
    list_filter = ('is_portal', 'is_active')
    search_fields = ('role', 'description')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    fieldsets = (
        (None, {'fields': ('role', 'description', 'is_portal', 'is_active', 'parent_role')}),
        ('Permissions', {'fields': ('permissions',)}),
        ('Metadata', {'fields': ('uuid', 'dt_created', 'dt_modified'), 'classes': ('collapse',)}),
    )


@admin.register(ModelRoleConfig)
class ModelRoleConfigAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for per-model role configurations."""
    # Scalar fields: allow_create, allow_delete, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, model_name, role, security_level, uuid, version
    list_display = ("ida", "allow_create", "allow_delete", "health_rating", "is_locked", "model_name", "is_active", "dt_created")
    list_filter = ('model_name', 'role', 'allow_create', 'allow_delete')
    search_fields = ('model_name', 'role')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    fieldsets = (
        (None, {'fields': ('model_name', 'role')}),
        ('Query Filtering', {'fields': ('query_filters',)}),
        ('Field Access', {'fields': ('view_fields', 'edit_fields')}),
        ('Permissions', {'fields': ('allow_create', 'allow_delete')}),
        ('Metadata', {'fields': ('uuid', 'dt_created', 'dt_modified'), 'classes': ('collapse',)}),
    )


@admin.register(ModelLinkConfig)
class ModelLinkConfigAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for model link/denormalization templates."""
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, model_name, security_level, uuid, version
    list_display = ("ida", "health_rating", "is_locked", "model_name", "security_level", "is_active", "dt_created")
    search_fields = ('model_name',)
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    fieldsets = (
        (None, {'fields': ('model_name',)}),
        ('Keywords', {'fields': ('keyword_fields',)}),
        ('Link Template', {'fields': ('link_template',)}),
        ('Metadata', {'fields': ('uuid', 'dt_created', 'dt_modified'), 'classes': ('collapse',)}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for User Profiles (user-contact-role linkage)."""
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, uuid, version
    list_display = ("ida", "health_rating", "is_locked", "security_level", "is_active", "dt_created")
    search_fields = ('user__username', 'user__email', 'contact__email', 'contact__company')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'cached_roles')
    raw_id_fields = ('user', 'contact')
    fieldsets = (
        (None, {'fields': ('user', 'contact')}),
        ('Cached Data', {'fields': ('cached_roles',)}),
        ('Metadata', {'fields': ('uuid', 'dt_created', 'dt_modified'), 'classes': ('collapse',)}),
    )
    
    @admin.display(description='cached_roles')
    def get_roles(self, obj):
        roles = obj.get_roles()
        return ', '.join(roles) if roles else '-'


def _threepane_redirect(self, request, extra_context=None):
    if not self.has_permission(request):
        return self.login(request)

    return HttpResponseRedirect(reverse("admin:threepane"))


def _resolve_registered_model(admin_site, app_label, model_name):
    for model, model_admin in admin_site._registry.items():
        opts = model._meta
        if opts.app_label == app_label and opts.model_name == model_name:
            return model, model_admin
    raise Http404


def _threepane_view(self, request):
    if not self.has_permission(request):
        return self.login(request)

    raw_app_list = self.get_app_list(request)
    enriched_app_list = []
    selected_app_label = request.GET.get("app")
    selected_model_name = request.GET.get("model")
    selected_object_id = request.GET.get("object")
    selected_model_entry = None
    selected_app_entry = None

    for app in raw_app_list:
        models = []
        for model_dict in app.get("models", []):
            model_class = model_dict.get("model")
            if not model_class:
                continue
            opts = model_class._meta
            new_dict = dict(model_dict)
            new_dict["tp_app_label"] = opts.app_label
            new_dict["tp_model_name"] = opts.model_name
            models.append(new_dict)
            if (
                selected_model_entry is None
                and selected_app_label == opts.app_label
                and selected_model_name == opts.model_name
            ):
                selected_model_entry = new_dict
                selected_app_entry = {**app, "models": models}
        enriched_app_list.append({**app, "models": models})

    if selected_app_entry is None and selected_app_label:
        for app in enriched_app_list:
            if app.get("app_label") == selected_app_label:
                selected_app_entry = app
                break

    if selected_model_entry is None and selected_app_entry:
        for model_dict in selected_app_entry.get("models", []):
            perms = model_dict.get("perms") or {}
            if perms.get("view") or perms.get("change"):
                selected_model_entry = model_dict
                break

    if selected_model_entry is None:
        for app in enriched_app_list:
            for model_dict in app.get("models", []):
                perms = model_dict.get("perms") or {}
                if perms.get("view") or perms.get("change"):
                    selected_model_entry = model_dict
                    selected_app_entry = app
                    break
            if selected_model_entry:
                break

    initial_app_label = ""
    initial_model_name = ""
    initial_list_url = ""
    initial_detail_url = ""

    if selected_model_entry:
        initial_app_label = selected_model_entry.get("tp_app_label") or ""
        initial_model_name = selected_model_entry.get("tp_model_name") or ""
        if initial_app_label and initial_model_name:
            initial_list_url = reverse(
                "admin:threepane_model_list",
                args=(initial_app_label, initial_model_name),
            )
            if selected_object_id:
                try:
                    model, model_admin = _resolve_registered_model(self, initial_app_label, initial_model_name)
                    obj = model_admin.get_object(request, selected_object_id)
                    if obj and (
                        model_admin.has_view_permission(request, obj=obj)
                        or model_admin.has_change_permission(request, obj=obj)
                    ):
                        initial_detail_url = reverse(
                            "admin:threepane_model_detail",
                            args=(initial_app_label, initial_model_name, selected_object_id),
                        )
                except Http404:
                    initial_detail_url = ""

    context = {
        **self.each_context(request),
        "app_list": enriched_app_list,
        "title": _("Admin (Three Pane)"),
        "initial_app_label": initial_app_label,
        "initial_model_name": initial_model_name,
        "initial_list_url": initial_list_url,
        "initial_detail_url": initial_detail_url,
    }

    request.current_app = self.name
    return TemplateResponse(request, "admin/threepane.html", context)


def _threepane_model_list(self, request, app_label, model_name):
    model, model_admin = _resolve_registered_model(self, app_label, model_name)

    if not (
        model_admin.has_view_permission(request)
        or model_admin.has_change_permission(request)
    ):
        raise PermissionDenied

    request.current_app = self.name
    response = model_admin.changelist_view(request)

    if isinstance(response, TemplateResponse):
        ctx = response.context_data or {}
        ctx.update(
            {
                "threepane": True,
                "threepane_list_url": request.get_full_path().split("?")[0],
                "threepane_app_label": app_label,
                "threepane_model_name": model_name,
            }
        )
        response.context_data = ctx
        response.template_name = "admin/threepane/changelist.html"

    return response


def _threepane_model_detail(self, request, app_label, model_name, object_id):
    model, model_admin = _resolve_registered_model(self, app_label, model_name)

    obj = model_admin.get_object(request, object_id)
    if not obj:
        raise Http404
    if not (
        model_admin.has_view_permission(request, obj=obj)
        or model_admin.has_change_permission(request, obj=obj)
    ):
        raise PermissionDenied

    fields_to_show = model_admin.get_fields(request, obj) or [field.name for field in obj._meta.local_fields]
    field_rows = []

    for field_name in fields_to_show:
        try:
            field = obj._meta.get_field(field_name)
        except Exception:
            continue

        raw_value = getattr(obj, field_name, None)

        if field.many_to_many:
            value = ", ".join(str(item) for item in raw_value.all()) if raw_value is not None else model_admin.empty_value_display
        else:
            value = display_for_field(raw_value, field, model_admin.empty_value_display)

        field_rows.append({"label": getattr(field, "verbose_name", field_name), "value": value})

    context = {
        **self.each_context(request),
        "opts": model._meta,
        "object": obj,
        "field_rows": field_rows,
        "threepane": True,
    }

    request.current_app = self.name
    return TemplateResponse(request, "admin/threepane/detail.html", context)


_original_get_urls = admin.site.get_urls


def _threepane_get_urls(self):
    urls = list(_original_get_urls())
    custom = [
        path("threepane/", self.admin_view(self.threepane_view), name="threepane"),
        path(
            "threepane/<str:app_label>/<str:model_name>/list/",
            self.admin_view(self.threepane_model_list),
            name="threepane_model_list",
        ),
        path(
            "threepane/<str:app_label>/<str:model_name>/<str:object_id>/",
            self.admin_view(self.threepane_model_detail),
            name="threepane_model_detail",
        ),
    ]
    return custom + urls


def _threepane_app_index(self, request, app_label, extra_context=None):
    if not self.has_permission(request):
        return self.login(request)

    base_url = reverse("admin:threepane")
    query = urlencode({"app": app_label})
    return HttpResponseRedirect(f"{base_url}?{query}")


admin.site.threepane_view = MethodType(_threepane_view, admin.site)
admin.site.threepane_model_list = MethodType(_threepane_model_list, admin.site)
admin.site.threepane_model_detail = MethodType(_threepane_model_detail, admin.site)
admin.site.get_urls = MethodType(_threepane_get_urls, admin.site)
admin.site.index = MethodType(_threepane_redirect, admin.site)
admin.site.app_index = MethodType(_threepane_app_index, admin.site)