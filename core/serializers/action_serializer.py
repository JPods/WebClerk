from rest_framework import serializers
from ..models import Action
from core.utils import get_accessible_fields

class ActionSerializer(serializers.ModelSerializer):
    """Serializer for Action model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Action
        fields = [
            'id', 'uuid', 'action', 'action_by', 'priority', 'difficulty', 'hours', 'percent',
            'status', 'quality', 'description', 'dt_action', 'dt_completed', 'dt_due',
            'dt_updated', 'comment', 'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'dt_action', 'dt_updated']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('actions', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)