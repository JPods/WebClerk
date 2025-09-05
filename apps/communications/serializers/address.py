# path: apps/communications/serializers/address.py
from rest_framework import serializers
from ..models import Location
from apps.core.utils import get_accessible_fields

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model with role-based field filtering.

    Removed legacy/non-existent fields: 'comment', 'dt_verified'. Added standard
    audit + active/version fields for parity with other serializers.
    """
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Location
        fields = [
            'id', 'uuid', 'address1', 'address2', 'address_type', 'city', 'country',
            'instructions', 'latitude', 'longitude', 'state', 'zip', 'full',
            'is_active', 'dt_created', 'dt_modified', 'version',
            'refs', 'prefs', 'metadata'
        ]
    read_only_fields = ['id', 'uuid', 'is_active', 'dt_created', 'dt_modified', 'version']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('addresses', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)