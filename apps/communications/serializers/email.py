# path: apps/communications/serializers/email.py
from rest_framework import serializers
from ..models import Email
from apps.core.utils import get_accessible_fields
from common.models import default_metadata 

class EmailSerializer(serializers.ModelSerializer):
    """Serializer for Email model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")
    status_display = serializers.CharField(read_only=True, help_text="Human-readable status derived from opt_out state")
    is_active = serializers.BooleanField(read_only=True, help_text="Active flag (from CoreModel)")

    class Meta:
        model = Email
        # Removed legacy/non-existent fields: 'comment', 'dt_verified', 'dt_bounced'.
        # 'comments' JSON envelope (from BaseModel) can be added later if needed.
        fields = [
            'id', 'uuid', 'email', 'attention', 'name', 'opt_out',
            'is_primary', 'is_verified', 'status_display', 'is_active',
            'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'status_display', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('emails', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)