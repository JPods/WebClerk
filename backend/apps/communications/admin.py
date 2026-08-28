# path: apps/communications/admin.py
from django.contrib import admin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from .models import Address, Email, Phone, Domain
from django.utils import timezone
from common.models import default_metadata 


@admin.register(Address)
class AddressAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Address model."""
    # Scalar fields: address1, address2, address_type, city, country, dt_created, dt_modified, full, health_rating, ida, instructions, is_active, is_archived, is_deleted, is_locked, latitude, longitude, security_level, state, uuid, version, zip
    list_display = ("ida", "address1", "address2", "address_type", "city", "country", "is_active", "dt_created")
    list_filter = ('address_type', 'country', 'state')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    readonly_fields = ('full',)
    fieldsets = (
        (None, {
            'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Additional Info', {
            'fields': ('comments', 'instructions', 'refs', 'prefs', 'metadata')
        }),
    )



@admin.register(Email)
class EmailAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Email model."""
    # Scalar fields: attention, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_primary, is_verified, name, opt_out, security_level, type, uuid, version
    list_display = ("ida", "name", "type", "email", "is_primary", "is_verified", "is_active", "dt_created")
    list_filter = ('opt_out', 'is_primary', 'is_verified')
    search_fields = ('email', 'name', 'attention')
    #readonly_fields = ('uuid', 'status_display')
    list_editable = ('is_primary', 'is_verified')
    actions = ['mark_as_verified', 'mark_as_primary']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'name', 'attention', 'contact_id')
        }),
        ('Status', {
            'fields': ('opt_out', 'is_primary')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )

   
@admin.register(Phone)
class PhoneAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Phone model."""
    # Scalar fields: attention, country_code, dt_created, dt_modified, format, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, number, opt_out, security_level, uuid, version
    list_display = ("ida", "name", "number", "attention", "country_code", "format", "is_active", "dt_created")
    list_filter = ('country_code', 'opt_out')  # Remove dt_verified from list_filter since it's now a property
    search_fields = ('number', 'name', 'attention')
    #readonly_fields = ('uuid')  # Add get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out', 'contact_id')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )


    

@admin.register(Domain)
class DomainAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    """Admin interface for Domain model."""
    # Scalar fields: count_accessed, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, path, security_level, sequence, status, type, uuid, version
    list_display = ("ida", "status", "type", "count_accessed", "health_rating", "is_active", "dt_created")
    list_filter = ('type',)  # Remove dt_verified from list_filter
    search_fields = ('path', 'type')
    #readonly_fields = ('uuid')  # Use get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('path', 'type', 'contact_id')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )

