# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/serializers/domain.py
from rest_framework import serializers
from ..models import Domain
from apps.core.utils import get_accessible_fields

class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Domain
        fields = [
            'id', 'uuid', 'path', 'type', 'comment', 'dt_verified', 'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('domains', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)