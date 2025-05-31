from rest_framework import serializers
from ..models import Action

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
            user_roles = request.user.role if hasattr(request.user, 'role') else []
            allowed_fields = self.get_allowed_fields(user_roles)
            # Remove fields not allowed for the user's role
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)

    def get_allowed_fields(self, user_roles):
        """Define fields accessible based on user roles."""
        if 'SUPER' in user_roles:
            return self.Meta.fields  # SUPER sees all fields
        elif 'ADMIN' in user_roles:
            # ADMIN sees all fields
            return self.Meta.fields
        else:
            # Other roles see limited fields
            return ['id', 'action', 'action_by', 'status', 'dt_due', 'refs']