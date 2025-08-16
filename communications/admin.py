# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/admin.py
from django.contrib import admin
from .models import Location, Email, Phone, Domain
from django.utils import timezone
from common.models import default_metadata 


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin interface for Location model."""
    list_display = ('id', 'address1', 'city', 'country', 'address_type', 'get_dt_verified', 'get_dt_created')
    list_filter = ('address_type', 'country', 'state')
    search_fields = ('address1', 'address2', 'city', 'zip', 'full')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated', 'get_dt_verified')
    fieldsets = (
        (None, {
            'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Verification', {
            'fields': ('get_dt_verified',)
        }),
        ('Additional Info', {
            'fields': ('comment', 'instructions', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_verified(self, obj):
        """Get verified timestamp from metadata.history.verified.dt."""
        return obj.dt_verified
    get_dt_verified.short_description = 'Verified'

    def get_dt_created(self, obj):  # FIXED: Proper indentation
        """Get creation timestamp from metadata.history.created.dt."""
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):  # FIXED: Proper indentation
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
    readonly_fields = ('uuid', 'status_display', 'get_dt_created', 'get_dt_updated', 'get_dt_verified', 'get_dt_bounced')
    list_editable = ('is_primary', 'is_verified')
    actions = ['mark_as_verified', 'mark_as_primary']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'name', 'attention')
        }),
        ('Status', {
            'fields': ('opt_out', 'is_primary', 'is_verified', 'get_dt_verified', 'get_dt_bounced')
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'status_display', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_verified(self, obj):
        """Get verified timestamp from metadata.history.verified.dt."""
        return obj.dt_verified  # This calls the property
    get_dt_verified.short_description = 'Verified'

    def get_dt_bounced(self, obj):
        """Get bounced timestamp from metadata.history.bounced.dt."""
        return obj.dt_bounced  # This calls the property
    get_dt_bounced.short_description = 'Bounced'

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.history.created.dt."""  # Fixed comment
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.history.updated.dt."""
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'

    def status_display(self, obj):
        """Display human-readable status."""
        return obj.status_display
    status_display.short_description = 'Status'

    def mark_as_verified(self, request, queryset):
        """Mark selected emails as verified by updating metadata."""
        count = 0
        for email in queryset:
            if not email.metadata:
                email.metadata = default_metadata()
            if 'history' not in email.metadata:
                email.metadata['history'] = default_metadata()['history']
            email.metadata['history']['verified']['dt'] = int(timezone.now().timestamp() * 1000)
            email.is_verified = True
            email.save()
            count += 1
        self.message_user(request, f'{count} emails marked as verified.')
    mark_as_verified.short_description = 'Mark selected emails as verified'

    def mark_as_primary(self, request, queryset):
        """Mark selected emails as primary."""
        count = queryset.update(is_primary=True)
        self.message_user(request, f'{count} emails marked as primary.')
    mark_as_primary.short_description = 'Mark selected emails as primary'
    
@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    """Admin interface for Phone model."""
    list_display = ('id', 'number', 'name', 'country_code', 'opt_out', 'get_dt_verified', 'get_dt_created')  # Changed dt_verified to get_dt_verified
    list_filter = ('country_code', 'opt_out')  # Remove dt_verified from list_filter since it's now a property
    search_fields = ('number', 'name', 'attention')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated', 'get_dt_verified')  # Add get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out')
        }),
        ('Verification', {
            'fields': ('get_dt_verified',)  # Changed from dt_verified to get_dt_verified
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_verified(self, obj):
        """Get verified timestamp from metadata.history.verified.dt."""
        return obj.dt_verified  # This calls the property
    get_dt_verified.short_description = 'Verified'

    def get_dt_created(self, obj):
        """Get creation timestamp from metadata.history.created.dt."""  # Fixed comment
        dt_ms = obj.metadata.get('history', {}).get('created', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_created.short_description = 'Created'

    def get_dt_updated(self, obj):
        """Get update timestamp from metadata.history.updated.dt."""  # Fixed comment
        dt_ms = obj.metadata.get('history', {}).get('updated', {}).get('dt')
        return timezone.datetime.fromtimestamp(dt_ms / 1000, tz=timezone.get_current_timezone()) if dt_ms else None
    get_dt_updated.short_description = 'Updated'
    

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Admin interface for Domain model."""
    list_display = ('id', 'path', 'type', 'get_dt_verified', 'get_dt_created')  # Use get_dt_verified
    list_filter = ('type',)  # Remove dt_verified from list_filter
    search_fields = ('path', 'type')
    readonly_fields = ('uuid', 'get_dt_created', 'get_dt_updated', 'get_dt_verified')  # Use get_dt_verified
    fieldsets = (
        (None, {
            'fields': ('path', 'type')
        }),
        ('Verification', {
            'fields': ('get_dt_verified',)  # Use get_dt_verified
        }),
        ('Additional Info', {
            'fields': ('comment', 'refs', 'prefs', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'get_dt_created', 'get_dt_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_dt_verified(self, obj):
        """Get verified timestamp from metadata.history.verified.dt."""
        return obj.dt_verified  # This calls the property
    get_dt_verified.short_description = 'Verified'

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

