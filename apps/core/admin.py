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
from apps.transactions.models import Project
from .models import Contact, Action, Setting, Template, Pending, SoftDeleteLedger


@admin.register(Contact)
class ContactAdmin(BaseUserAdmin):
    """Admin interface for Contact model (custom user model)."""
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
    list_display = scalar_fields
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'name_first', 'name_last', 'company')
    readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
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
class ActionAdmin(admin.ModelAdmin):
    """Admin interface for Action model."""
    list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
    list_filter = ('kanban_column', 'status', 'priority')
    search_fields = ('project_id', 'action')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    # Keep scalar then object fields alphabetical for detail view coherence.
    scalar_fields = (
        'action_id',
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
    
    def get_action_title(self, obj):
        action_dict = obj.action or {}
        return action_dict.get('en') or action_dict.get('bn') or action_dict.get('ar') or 'Untitled'
    get_action_title.short_description = 'Action'

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
class SettingAdmin(admin.ModelAdmin):
    """Admin interface for Setting model."""
    list_display = ('id', 'name', 'purpose', 'parent_model', 'role')
    list_filter = ('purpose', 'role')
    search_fields = ('name', 'purpose', 'parent_model')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """Admin interface for Template model."""
    list_display = ('id', 'name', 'purpose', 'dt_processed')
    list_filter = ('purpose',)
    search_fields = ('name', 'purpose')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(Pending)
class PendingAdmin(admin.ModelAdmin):
    """Admin interface for Pending model."""
    list_display = ('id', 'model_name', 'record_id', 'purpose', 'dt_processed')
    list_filter = ('model_name', 'purpose')
    search_fields = ('model_name', 'record_id', 'name')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(SoftDeleteLedger)
class SoftDeleteLedgerAdmin(admin.ModelAdmin):
    """Admin interface for SoftDeleteLedger model."""
    list_display = ('id', 'target', 'dt_purge', 'dt_created')
    list_filter = ('contenttype_id', 'dt_purge')
    search_fields = ('contenttype_id__model', 'object_id')
    readonly_fields = ('dt_created',)

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