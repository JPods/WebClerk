# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/admin.py
from string import Template
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Contact, Setting, Pending, Action, Template

@admin.register(Contact)
class ContactAdmin(UserAdmin):
    """Admin interface for Contact model with Universal API support"""
    
    # Fields to display in the list view (FIXED - removed is_email_verified)
    list_display = ['id', 'email', 'name_first', 'name_last', 'company', 'role', 'comment', 'is_active', 'date_joined']

    # Fields to filter by (FIXED - removed is_email_verified)
    list_filter = ['id', 'role', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
    
    # Fields to search
    search_fields = ['email', 'name_first', 'name_last', 'company']
    
    # Fields to organize in the detail view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix')
        }),
        ('Business Info', {
            'fields': ('company', 'title', 'department')
        }),
        ('Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'metadata', 'refs', 'prefs')
        }),
    )
    
    # Fields for creating new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name_first', 'name_last', 'password1', 'password2', 'role'),
        }),
    )
    
    # Use email as the ordering field
    ordering = ('email',)
    
    # Make role editable in list view
    list_editable = ['role']
    
    # Show role choices in filter
    def get_role_display(self, obj):
        return obj.get_role_display_name()
    get_role_display.short_description = 'Role'

admin.site.register(Setting)
admin.site.register(Pending)
admin.site.register(Action)
admin.site.register(Template)
