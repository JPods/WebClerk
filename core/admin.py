from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Contact, Action, Template, Setting

class ContactAdmin(UserAdmin):
    model = Contact
    list_display = ('email', 'name_first', 'name_last', 'get_roles', 'is_email_verified', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'is_email_verified', 'role')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'name_first', 'name_last', 'name_middle', 'role',
                'company', 'prefix', 'salutation', 'suffix', 'rank', 'attention'
            )
        }),
        ('Verification', {'fields': ('is_email_verified', 'verification_code', 'verification_code_expiry')}),
        ('Additional Info', {'fields': ('comment_alert', 'opt_out', 'publish', 'comment', 'prefs')}),
        ('Metadata', {'fields': ('refs', 'metadata')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'name_first', 'name_last', 'name_middle', 'role', 'password1', 'password2',
                'is_active', 'is_staff', 'is_email_verified', 'company', 'prefix', 'salutation',
                'suffix', 'rank', 'attention', 'comment_alert', 'opt_out', 'publish', 'comment',
                'refs', 'prefs', 'metadata'
            ),
        }),
    )
    search_fields = ('email', 'name_first', 'name_last')
    ordering = ('email',)

    def get_roles(self, obj):
        return ", ".join(obj.role) if obj.role else "None"
    get_roles.short_description = 'Roles'

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('action', 'uuid', 'action_by', 'status', 'dt_action')
    list_filter = ('status', 'priority', 'dt_action')
    search_fields = ('action', 'action_by', 'description')
    fieldsets = (
        (None, {'fields': ('uuid', 'action', 'action_by')}),
        ('Details', {'fields': ('priority', 'difficulty', 'hours', 'percent', 'status', 'quality', 'description')}),
        ('Dates', {'fields': ('dt_action', 'dt_completed', 'dt_due', 'dt_updated')}),
        ('Additional Info', {'fields': ('comment', 'refs', 'prefs', 'metadata')}),
    )

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'purpose', 'table_name')
    list_filter = ('purpose',)
    search_fields = ('name', 'purpose', 'table_name')
    fieldsets = (
        (None, {'fields': ('uuid', 'name', 'purpose', 'table_name')}),
        ('Additional Info', {'fields': ('comment', 'refs', 'prefs', 'metadata')}),
    )

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'is_active', 'purpose', 'role')
    list_filter = ('is_active', 'role')
    search_fields = ('name', 'purpose', 'role', 'table_name')
    fieldsets = (
        (None, {'fields': ('uuid', 'is_active', 'name', 'purpose', 'role', 'table_name')}),
        ('Additional Info', {'fields': ('comment', 'refs', 'prefs', 'metadata')}),
    )

admin.site.register(Contact, ContactAdmin)