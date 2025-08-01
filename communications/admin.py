from django.contrib import admin
from .models import Address, Email, Phone, Domain
from django.utils import timezone

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Address model."""
    list_display = ('id', 'address1', 'city', 'country', 'address_type', 'dt_verified', 'get_dt_created')
    list_filter = ('address_type', 'country', 'state', 'dt_verified')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Verification', {
            'fields': ('dt_verified',)
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
        """Get creation timestamp from metadata.history.created.dt."""
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.history.updated.dt."""
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    """Admin interface for Email model."""
    list_display = ('id', 'email', 'name', 'status_display', 'is_primary', 'is_verified', 'get_dt_created')
    list_filter = ('opt_out', 'is_primary', 'is_verified')
    search_fields = ('email', 'name', 'attention')
    readonly_fields = ('uuid', 'status_display', 'get_dt_created', 'get_dt_updated')
    list_editable = ('is_primary', 'is_verified')
    actions = ['mark_as_verified', 'mark_as_primary']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'name', 'attention')
        }),
        ('Status', {
            'fields': ('opt_out', 'is_primary', 'is_verified', 'dt_verified', 'dt_bounced')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'status_display', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def mark_as_verified(self, request, queryset):
        """Mark selected emails as verified."""
        from django.utils import timezone
        count = queryset.update(is_verified=True, dt_verified=timezone.now())
        self.message_user(request, f'{count} emails marked as verified.')
    mark_as_verified.short_description = 'Mark selected emails as verified'

    def mark_as_primary(self, request, queryset):
        """Mark selected emails as primary."""
        count = queryset.update(is_primary=True)
        self.message_user(request, f'{count} emails marked as primary.')
    mark_as_primary.short_description = 'Mark selected emails as primary'

    def status_display(self, obj):
        """Display human-readable status."""
        return obj.status_display
    status_display.short_description = 'Status'

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.history.created.dt."""
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dt_updated."""
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    """Admin interface for Phone model."""
    list_display = ('id', 'number', 'name', 'country_code', 'opt_out', 'dt_verified', 'get_dt_created')
    list_filter = ('country_code', 'opt_out', 'dt_verified')
    search_fields = ('number', 'name', 'attention')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out')
        }),
        ('Verification', {
            'fields': ('dt_verified',)
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
        """Get creation timestamp from metadata.health.dt_created."""
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.health.dt_updated."""
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain model."""
    list_display = ('id', 'path', 'type', 'dt_verified', 'get_dt_created')
    list_filter = ('type', 'dt_verified')
    search_fields = ('path', 'type')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated')
    fieldsets = (
        (None, {
            'fields': ('path', 'type')
        }),
        ('Verification', {
            'fields': ('dt_verified',)
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
        """Get creation timestamp from metadata.history.created.dt."""
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.history.updated.dt."""
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'