from django.contrib import admin
from .models import Address, Email, Phone, Domain

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Address model."""
    list_display = ('id', 'uuid', 'address1', 'city', 'country', 'address_type', 'dt_created')
    list_filter = ('address_type', 'country', 'state')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    readonly_fields = ('id', 'uuid', 'dt_created', 'dt_updated')
    fieldsets = (
        (None, {
            'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Additional Info', {
            'fields': ('instructions', 'comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('dt_created', 'dt_updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    """Admin interface for Email model."""
    list_display = ('id', 'uuid', 'address', 'name', 'opt_out', 'dt_created')
    list_filter = ('opt_out',)
    search_fields = ('address', 'name', 'attention')
    readonly_fields = ('id', 'uuid', 'dt_created', 'dt_updated')
    fieldsets = (
        (None, {
            'fields': ('address', 'name', 'attention', 'opt_out')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('dt_created', 'dt_updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    """Admin interface for Phone model."""
    list_display = ('id', 'uuid', 'number', 'name', 'country_code', 'opt_out', 'dt_created')
    list_filter = ('country_code', 'opt_out')
    search_fields = ('number', 'name', 'attention')
    readonly_fields = ('id', 'uuid', 'dt_created', 'dt_updated')
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('dt_created', 'dt_updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain model."""
    list_display = ('id', 'uuid', 'path', 'type', 'dt_created')
    list_filter = ('type',)
    search_fields = ('path', 'type')
    readonly_fields = ('id', 'uuid', 'dt_created', 'dt_updated')
    fieldsets = (
        (None, {
            'fields': ('path', 'type')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('dt_created', 'dt_updated'),
            'classes': ('collapse',)
        }),
    )