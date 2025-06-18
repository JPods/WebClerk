from django.contrib import admin
from .models import Address, Email, Phone, Domain
from django.utils import timezone

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Address model."""
    list_display = ('id', 'address1', 'city', 'country', 'address_type', 'get_dt_created')
    list_filter = ('address_type', 'country', 'state')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Additional Info', {
            'fields': ('comment', 'instructions', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.health.dtCreated."""
        dt_ms = obj.metadata.get('health', {}).get('dtCreated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dtUpdated."""
        dt_ms = obj.metadata.get('health', {}).get('dtUpdated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    """Admin interface for Email model."""
    list_display = ('id', 'address', 'name', 'opt_out', 'get_dt_created')
    list_filter = ('opt_out',)
    search_fields = ('address', 'name', 'attention')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('address', 'name', 'attention', 'opt_out')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.health.dtCreated."""
        dt_ms = obj.metadata.get('health', {}).get('dtCreated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dtUpdated."""
        dt_ms = obj.metadata.get('health', {}).get('dtUpdated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    """Admin interface for Phone model."""
    list_display = ('id', 'number', 'name', 'country_code', 'opt_out', 'get_dt_created')
    list_filter = ('country_code', 'opt_out')
    search_fields = ('number', 'name', 'attention')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.health.dtCreated."""
        dt_ms = obj.metadata.get('health', {}).get('dtCreated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dtUpdated."""
        dt_ms = obj.metadata.get('health', {}).get('dtUpdated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain model."""
    list_display = ('id', 'path', 'type', 'get_dt_created')
    list_filter = ('type',)
    search_fields = ('path', 'type')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('path', 'type')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.health.dtCreated."""
        dt_ms = obj.metadata.get('health', {}).get('dtCreated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dtUpdated."""
        dt_ms = obj.metadata.get('health', {}).get('dtUpdated')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'