# path: apps/communications/serializers/domain.py
from rest_framework import serializers
from ..models import Domain
from common.base_serializers import RoleAwareModelSerializer

class DomainSerializer(RoleAwareModelSerializer):
    """Serializer for Domain model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Domain
        fields = [
            'id', 'uuid', 'path', 'type', 'comment', 'status', 'security_level', 'sequence', 'count_accessed', 'is_active',
            'refs', 'prefs', 'metadata', 'dt_created', 'dt_modified', 'version'
        ]
    read_only_fields = ['id', 'uuid', 'count_accessed', 'dt_created', 'dt_modified', 'version']

            # model_name-only world; no model_name attribute