from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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
    list_display = ('id', 'get_action_title', 'kanban_column', 'status', 'priority', 'dt_created')
    list_filter = ('kanban_column', 'status', 'priority')
    search_fields = ('id_project', 'action')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    
    def get_action_title(self, obj):
        action_dict = obj.action or {}
        return action_dict.get('en') or action_dict.get('bn') or action_dict.get('ar') or 'Untitled'
    get_action_title.short_description = 'Action'


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
    list_filter = ('content_type', 'dt_purge')
    search_fields = ('content_type__model', 'object_id')
    readonly_fields = ('dt_created',)