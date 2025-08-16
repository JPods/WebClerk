from rest_framework import serializers
from ..models import Location
from core.utils import get_accessible_fields

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Location
        fields = [
            'id', 'uuid', 'address1', 'address2', 'address_type', 'city', 'country',
            'instructions', 'latitude', 'longitude', 'state', 'zip', 'full', 'comment',
            'dt_verified', 'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('addresses', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)