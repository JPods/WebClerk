# path: apps/communications/admin.py
from django.contrib import admin
from .models import Address, Email, Phone, Domain
from django.utils import timezone
from common.models import default_metadata 


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Address model."""
    list_display = ('id', 'address1', 'city', 'country', 'address_type')
    list_filter = ('address_type', 'country', 'state')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    #readonly_fields = ('uuid')
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
class EmailAdmin(admin.ModelAdmin):
    """Admin interface for Email model."""
    list_display = ('id', 'email', 'name', 'is_primary', 'is_verified')
    list_filter = ('opt_out', 'is_primary', 'is_verified')
    search_fields = ('email', 'name', 'attention')
    #readonly_fields = ('uuid', 'status_display')
    list_editable = ('is_primary', 'is_verified')
    actions = ['mark_as_verified', 'mark_as_primary']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'name', 'attention')
        }),
        ('Status', {
            'fields': ('opt_out', 'is_primary')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )

   
@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    """Admin interface for Phone model."""
    list_display = ('id', 'number', 'name', 'country_code', 'opt_out')  # Changed dt_verified to get_dt_verified
    list_filter = ('country_code', 'opt_out')  # Remove dt_verified from list_filter since it's now a property
    search_fields = ('number', 'name', 'attention')
    #readonly_fields = ('uuid')  # Add get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )


    

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain model."""
    list_display = ('id', 'path', 'type')  # Use get_dt_verified
    list_filter = ('type',)  # Remove dt_verified from list_filter
    search_fields = ('path', 'type')
    #readonly_fields = ('uuid')  # Use get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('path', 'type')
        }),
        ('Additional Info', {
            'fields': ('comments', 'refs', 'prefs', 'metadata')
        }),
    )

