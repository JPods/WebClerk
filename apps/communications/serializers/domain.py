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
            'id', 'uuid', 'path', 'type', 'comment', 'status', 'security_level', 'sequence', 'count_accessed', 'is_active',
            'refs', 'prefs', 'metadata', 'created_dt', 'modified_dt', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'count_accessed', 'created_dt', 'modified_dt', 'version']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('domains', mode, request.user)
            # Fallback: if no settings configured but privileged role, keep all fields
            privileged = getattr(request.user, 'role', '') in {'staff', 'admin'} or getattr(request.user, 'is_superuser', False)
            if allowed_fields:
                for field_name in set(self.fields) - set(allowed_fields):
                    self.fields.pop(field_name, None)
            elif not privileged:
                # Non-privileged with no config: expose a minimal safe subset
                minimal = {'id','uuid','path','type','comment'}
                for field_name in list(self.fields.keys()):
                    if field_name not in minimal:
                        self.fields.pop(field_name, None)