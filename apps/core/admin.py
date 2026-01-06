from types import MethodType

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin.helpers import ActionForm
from django.contrib.admin.utils import display_for_field
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.transactions.models import Project
from .models import Contact, Action, Setting, Template, Pending, SoftDeleteLedger


@admin.register(Contact)
class ContactAdmin(BaseUserAdmin):
    """Admin interface for Contact model (custom user model)."""
    list_display = ('id', 'email', 'name_first', 'name_last', 'company', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'name_first', 'name_last', 'company')
    readonly_fields = ('dt_joined', 'uuid')
    ordering = ('name_last', 'name_first')
    
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
            'fields': ('company', 'title', 'department'),
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('role', 'is_active', 'is_staff'),
        }),
    )
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix')}),
        ('Company info', {'fields': ('company', 'title', 'department')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('dt_joined',)}),
        ('Additional Info', {'fields': ('comment', 'refs', 'prefs', 'metadata')}),
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


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """Admin interface for Action model."""
    list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_created')
    list_filter = ('kanban_column', 'status', 'priority')
    search_fields = ('project_id', 'action')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    actions = ['assign_project_id']

    class AssignProjectIdActionForm(ActionForm):
        project_id = forms.CharField(required=True, label='Project ID')

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
    list_display = ('id', 'name', 'purpose', 'model_target', 'role')
    list_filter = ('purpose', 'role')
    search_fields = ('name', 'purpose', 'model_target')
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
    list_display = ('id', 'model_name', 'id_record', 'purpose', 'dt_processed')
    list_filter = ('model_name', 'purpose')
    search_fields = ('model_name', 'id_record', 'name')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')


@admin.register(SoftDeleteLedger)
class SoftDeleteLedgerAdmin(admin.ModelAdmin):
    """Admin interface for SoftDeleteLedger model."""
    list_display = ('id', 'target', 'dt_purge', 'dt_created')
    list_filter = ('contenttype_id', 'dt_purge')
    search_fields = ('contenttype_id__model', 'object_id')
    readonly_fields = ('dt_created',)


def _three_column_index(self, request, extra_context=None):
    if not self.has_permission(request):
        return self.login(request)

    app_list = self.get_app_list(request)
    selected_model_label = request.GET.get("model")
    selected_object_id = request.GET.get("object")

    selected_model_dict = None
    selected_model_admin = None
    selected_model_meta = None

    if selected_model_label:
        for app in app_list:
            for model_dict in app.get("models", []):
                model_class = model_dict.get("model")
                if not model_class:
                    continue
                if model_class._meta.label_lower == selected_model_label:
                    selected_model_dict = model_dict
                    selected_model_admin = self._registry.get(model_class)
                    selected_model_meta = model_class._meta
                    break
            if selected_model_dict:
                break

    object_entries = []
    detail_rows = []
    detail_obj = None
    detail_change_url = None
    permission_denied = False

    if selected_model_admin:
        has_view_perm = (
            selected_model_admin.has_view_permission(request)
            or selected_model_admin.has_change_permission(request)
        )
        if has_view_perm:
            queryset = selected_model_admin.get_queryset(request)
            ordering = selected_model_admin.get_ordering(request)
            if ordering:
                queryset = queryset.order_by(*ordering)
            queryset = queryset[:50]
            if selected_model_meta:
                list_url_base = reverse('admin:index')
                for obj in queryset:
                    pk_value = obj.pk
                    object_entries.append({
                        "pk": pk_value,
                        "label": str(obj),
                        "is_selected": selected_object_id is not None and str(pk_value) == str(selected_object_id),
                        "url": f"{list_url_base}?model={selected_model_meta.label_lower}&object={pk_value}",
                    })

                if selected_object_id:
                    target_obj = selected_model_admin.get_object(request, selected_object_id)
                    if target_obj and (
                        selected_model_admin.has_view_permission(request, target_obj)
                        or selected_model_admin.has_change_permission(request, target_obj)
                    ):
                        detail_obj = target_obj
                        detail_change_url = reverse(
                            f"admin:{selected_model_meta.app_label}_{selected_model_meta.model_name}_change",
                            args=[target_obj.pk],
                        )
                        for field in selected_model_meta.concrete_fields:
                            if not hasattr(target_obj, field.name):
                                continue
                            value = getattr(target_obj, field.name)
                            rendered = display_for_field(value, field, self.empty_value_display)
                            detail_rows.append({
                                "label": getattr(field, "verbose_name", field.name),
                                "value": rendered,
                            })
        else:
            permission_denied = True
    elif selected_model_label:
        permission_denied = True

    context = {
        **self.each_context(request),
        "title": _("Site administration"),
        "app_list": app_list,
        "selected_model_label": selected_model_meta.label_lower if selected_model_meta else None,
        "selected_model_name": selected_model_meta.verbose_name if selected_model_meta else None,
        "selected_model_plural": selected_model_meta.verbose_name_plural if selected_model_meta else None,
        "object_entries": object_entries,
        "object_detail_obj": detail_obj,
        "object_detail_rows": detail_rows,
        "object_change_url": detail_change_url,
        "selected_model_add_url": selected_model_dict.get("add_url") if selected_model_dict else None,
        "permission_denied_model": permission_denied,
    }

    if extra_context:
        context.update(extra_context)

    request.current_app = self.name
    template = self.index_template or "admin/index.html"
    return TemplateResponse(request, template, context)


admin.site.index_template = "core_admin/index.html"
admin.site.index = MethodType(_three_column_index, admin.site)