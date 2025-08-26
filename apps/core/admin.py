# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/admin.py
from string import Template
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Contact, Setting, Pending, Action, Template
from django.db import models

def get_char_fields(model):
    return [f.name for f in model._meta.fields if f.get_internal_type() == 'CharField']

def get_all_fields(model):
    return [f.name for f in model._meta.fields]

@admin.register(Contact)
class ContactAdmin(UserAdmin):
    """Admin interface for Contact model with Universal API support"""
    
    # Fields to display in the list view (FIXED - removed is_email_verified)
    list_display = ['id', 'email', 'name_first', 'name_last', 'company', 'role', 'comment', 'is_active', 'date_joined']

    # Fields to filter by (FIXED - removed is_email_verified)
    list_filter = ['id', 'role', 'is_active', 'is_staff', 'is_superuser']
    
    # Fields to search
    search_fields = ['email', 'name_first', 'name_last', 'company']
    
    # Fields to organize in the detail view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix','role')
        }),
        ('Business Info', {
            'fields': ('company', 'title', 'department')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
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

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):  # <-- Use admin.ModelAdmin, not UserAdmin
    """Admin interface for Setting model showing all CharFields and all fields in list_display."""
    model = Setting

    # # Get all CharFields
    # char_fields = [f.name for f in Setting._meta.fields if isinstance(f, models.CharField)]
    # # Get all fields
    # all_fields = [f.name for f in Setting._meta.fields]

    list_display = get_char_fields(Setting)
    list_filter = get_char_fields(Setting)
    search_fields = get_char_fields(Setting)
    ordering = get_all_fields(Setting)

@admin.register(Pending)
class PendingAdmin(admin.ModelAdmin):
    list_display = get_char_fields(Pending)
    list_filter = get_char_fields(Pending)
    search_fields = get_char_fields(Pending)
    ordering = get_all_fields(Pending)

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = get_char_fields(Action)
    list_filter = get_char_fields(Action)
    search_fields = get_char_fields(Action)
    ordering = get_all_fields(Action)

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = get_char_fields(Template)
    list_filter = get_char_fields(Template)
    search_fields = get_char_fields(Template)
    ordering = get_all_fields(Template)


